#!/bin/bash

set -eu

ssh_cmd="ssh -F /srv/magnum/.ssh/config root@localhost"
launcher_path="/usr/local/bin/magnum-reconcile-launcher"

echo "Installing reconciler launcher: ${launcher_path}"

cat <<'EOF' | $ssh_cmd "cat > '${launcher_path}.tmp'"
#!/bin/bash

set -euo pipefail

mode="${1:-run-once}"
shift || true

heat_params_file="/etc/sysconfig/heat-params"
cache_root="/opt/magnum-reconciler"
lock_file="/var/lib/magnum/reconciler.lock"
result_file="/var/lib/magnum/reconciler-last-run.json"
log_file="/var/log/magnum-reconcile.log"
state_file="/var/lib/magnum/reconciler-state.json"
run_state_file="/var/lib/magnum/reconciler-run.json"
state_backup_dir="/var/lib/magnum/reconciler-state-backups"
pulumi_state_root="/var/lib/magnum/pulumi"
pulumi_backup_dir="/var/lib/magnum/pulumi-backups"
work_dir="/var/lib/magnum"
binary_name="bootstrap"
default_repository_url="https://github.com/ventus-ag/magnum-bootstrap"

log() {
    printf '%s %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*"
}

mkdir -p \
    "${cache_root}" \
    "${work_dir}" \
    "$(dirname "${log_file}")" \
    "${state_backup_dir}" \
    "${pulumi_state_root}" \
    "${pulumi_backup_dir}"

touch "${log_file}"
chmod 600 "${log_file}"

if [ -f "${heat_params_file}" ]; then
    set -a
    # shellcheck disable=SC1090
    . "${heat_params_file}"
    set +a
fi

# Last-resort reconciler version. Used ONLY when nothing is installed and the
# latest release cannot be resolved. The normal path auto-upgrades to the latest
# published release; this is the floor we can always boot from.
fallback_version="v1.0.0"

repository_url="${RECONCILER_REPOSITORY_URL:-${default_repository_url}}"
pinned_version="${RECONCILER_VERSION:-}"
pinned_binary_url="${RECONCILER_BINARY_URL:-}"
expected_sha256="${RECONCILER_BINARY_URL_SHA256:-}"
lock_timeout_seconds="${RECONCILER_LOCK_TIMEOUT_SECONDS:-900}"
# Overall reconcile timeout. MUST stay a safe margin below Heat's stack
# update_timeout so the reconciler self-cancels, reports failure, and releases
# this flock BEFORE Heat gives up — otherwise a wedged run keeps holding the
# lock after Heat fails the deployment and every retry blocks on it.
run_timeout_seconds="${RECONCILER_RUN_TIMEOUT_SECONDS:-4800}"

# Symlink to the last-known-good version dir. Used as the silent fallback target
# whenever an upgrade attempt fails.
current_link="${cache_root}/current"

# Resolve the newest published release tag by following the GitHub
# releases/latest redirect (an HTML endpoint, so no API rate limiting). Prints
# the tag (e.g. v1.2.3) on success; returns non-zero on any failure.
resolve_latest_tag() {
    local final_url tag
    final_url="$(curl -fsSL -I -o /dev/null -w '%{url_effective}' \
        "${repository_url}/releases/latest" 2>/dev/null)" || return 1
    [ -n "${final_url}" ] || return 1
    tag="${final_url##*/}"
    case "${tag}" in
        v[0-9]*) printf '%s' "${tag}" ;;
        *) return 1 ;;
    esac
}

# Download + verify + atomically install a reconciler binary.
#   $1 = download URL   $2 = destination version dir   $3 = expected sha256 (opt)
# Returns non-zero on any download/verification failure (callers fall back).
download_and_install() {
    local dl_url="$1" dest_dir="$2" dl_sha="$3" tmp_binary
    tmp_binary="$(mktemp)"

    log "Downloading reconciler url=${dl_url}"
    if ! curl -fsSL "${dl_url}" -o "${tmp_binary}"; then
        log "Download failed url=${dl_url}"
        rm -f "${tmp_binary}"
        return 1
    fi

    if [ -z "${dl_sha}" ]; then
        dl_sha=$(curl -fsSL "${dl_url}.sha256" 2>/dev/null | awk '{print $1}') || true
    fi
    if [ -n "${dl_sha}" ]; then
        if ! printf '%s  %s\n' "${dl_sha}" "${tmp_binary}" | sha256sum -c - >/dev/null 2>&1; then
            log "Checksum verification failed url=${dl_url}"
            rm -f "${tmp_binary}"
            return 1
        fi
    else
        log "WARNING: could not obtain SHA256 checksum for ${dl_url}, skipping verification"
    fi

    rm -rf "${dest_dir}.tmp"
    mkdir -p "${dest_dir}.tmp"
    mv "${tmp_binary}" "${dest_dir}.tmp/${binary_name}"
    chmod 755 "${dest_dir}.tmp/${binary_name}"
    rm -rf "${dest_dir}"
    mv "${dest_dir}.tmp" "${dest_dir}"
    if [ -n "${dl_sha}" ]; then
        printf '%s\n' "${dl_sha}" > "${dest_dir}/${binary_name}.sha256" 2>/dev/null || true
    fi
    return 0
}

# Point binary_path at the currently-installed reconciler so a failed upgrade
# keeps the node running on the last-known-good binary. Returns non-zero when no
# usable current binary exists.
run_current_fallback() {
    local fb_path
    fb_path="${current_link}/${binary_name}"
    if [ -x "${fb_path}" ]; then
        log "FALLBACK: $1; running currently-installed reconciler ($(readlink -f "${current_link}" 2>/dev/null || printf '%s' "${current_link}"))"
        binary_path="${fb_path}"
        return 0
    fi
    return 1
}

# Bound cache disk use: each cached version dir holds a ~105 MiB binary, and
# auto-upgrade adds a new one per release. Keep the few most-recent version dirs
# (newest by mtime) plus whatever the current symlink points at; delete older
# dirs and any stray *.tmp left by an interrupted install. Best-effort: never
# fails the run, never deletes the live current/target dir.
prune_cache() {
    local keep=3 count=0 d real_current
    real_current="$(readlink -f "${current_link}" 2>/dev/null || true)"
    for d in $(ls -1dt "${cache_root}"/*/ 2>/dev/null); do
        d="${d%/}"
        [ "${d}" = "${current_link}" ] && continue
        case "${d}" in
            *.tmp) rm -rf "${d}" 2>/dev/null || true; continue ;;
        esac
        count=$((count + 1))
        [ "${count}" -le "${keep}" ] && continue
        [ "$(readlink -f "${d}" 2>/dev/null)" = "${real_current}" ] && continue
        log "Pruning old cached reconciler ${d##*/}"
        rm -rf "${d}" 2>/dev/null || true
    done
}

exec 9>"${lock_file}"
if [ "${mode}" = "run-periodic" ]; then
    if ! flock -n 9; then
        log "Reconcile lock is busy, skipping periodic run"
        exit 0
    fi
else
    if ! flock -n 9; then
        log "Reconcile lock is busy (another run is active), waiting up to ${lock_timeout_seconds}s..."
        if ! flock -w "${lock_timeout_seconds}" 9; then
            log "ERROR: Timed out waiting for reconcile lock after ${lock_timeout_seconds}s"
            exit 1
        fi
        log "Lock acquired after wait"
    fi
fi

# --- Resolve which reconciler to run -------------------------------------
# Priority:
#   1. RECONCILER_BINARY_URL set -> explicit override (e2e / operator pin)
#   2. RECONCILER_VERSION set    -> pinned release tag (auto-upgrade disabled)
#   3. neither set               -> auto-latest: resolve the newest release
target_version=""
target_url=""

if [ -n "${pinned_binary_url}" ]; then
    target_url="${pinned_binary_url}"
    target_version="${pinned_version:-pinned}"
    log "Reconciler pinned to explicit URL version=${target_version} url=${target_url}"
elif [ -n "${pinned_version}" ]; then
    target_version="${pinned_version}"
    target_url="${repository_url}/releases/download/${target_version}/bootstrap"
    log "Reconciler pinned to release version=${target_version}"
else
    log "Resolving latest reconciler release from ${repository_url}"
    if latest_tag="$(resolve_latest_tag)"; then
        target_version="${latest_tag}"
        target_url="${repository_url}/releases/download/${target_version}/bootstrap"
        log "Latest reconciler release resolved version=${target_version}"
    else
        log "Could not resolve latest reconciler release"
    fi
fi

# Migration: if no current pointer exists yet but a cached version dir does,
# adopt it so a failed upgrade has a fallback target (older launchers did not
# maintain this symlink).
if [ ! -e "${current_link}" ]; then
    for cand in "${cache_root}/${fallback_version}" "${cache_root}"/*/; do
        cand="${cand%/}"
        [ "${cand}" = "${current_link}" ] && continue
        if [ -x "${cand}/${binary_name}" ]; then
            ln -sfn "${cand}" "${current_link}"
            log "Adopted existing cached reconciler as current: ${cand##*/}"
            break
        fi
    done
fi

binary_path=""

if [ -n "${target_version}" ] && [ -n "${target_url}" ]; then
    binary_dir="${cache_root}/${target_version}"
    candidate="${binary_dir}/${binary_name}"

    # Decide whether to (re)download the target. A brand-new release tag has no
    # cache dir yet, so this is also the "newer version available" path.
    need_download=false
    release_sha256="${expected_sha256}"
    if [ ! -x "${candidate}" ]; then
        need_download=true
    elif [ -f "${result_file}" ]; then
        last_status=$(grep -o '"status":"[^"]*"' "${result_file}" 2>/dev/null | head -1 | cut -d'"' -f4) || true
        if [ "${last_status}" = "failed" ]; then
            log "Previous run failed, re-downloading reconciler ${target_version}"
            need_download=true
        fi
    fi

    if [ "${need_download}" = "false" ]; then
        # Integrity / drift check against the release checksum.
        if [ -z "${release_sha256}" ]; then
            release_sha256=$(curl -fsSL "${target_url}.sha256" 2>/dev/null | awk '{print $1}') || true
        fi
        if [ -n "${release_sha256}" ]; then
            current_binary_sha256=$(sha256sum "${candidate}" | awk '{print $1}')
            if [ "${current_binary_sha256}" != "${release_sha256}" ]; then
                log "Cached ${target_version} checksum differs from release, re-downloading"
                need_download=true
            fi
        else
            log "Release checksum unavailable, keeping cached ${target_version}"
        fi
    fi

    if [ "${need_download}" = "true" ]; then
        if download_and_install "${target_url}" "${binary_dir}" "${release_sha256}"; then
            binary_path="${candidate}"
        elif ! run_current_fallback "download of ${target_version} failed"; then
            log "ERROR: download of ${target_version} failed and no installed reconciler to fall back to"
            exit 1
        fi
    else
        log "Reconciler ${target_version} already installed and verified"
        binary_path="${candidate}"
    fi
else
    # Auto-latest resolution failed: keep running the installed binary.
    if ! run_current_fallback "latest reconciler release could not be resolved"; then
        # Nothing installed at all -> bootstrap the last-resort fallback version.
        log "No installed reconciler; bootstrapping last-resort fallback ${fallback_version}"
        binary_dir="${cache_root}/${fallback_version}"
        candidate="${binary_dir}/${binary_name}"
        fallback_url="${repository_url}/releases/download/${fallback_version}/bootstrap"
        if download_and_install "${fallback_url}" "${binary_dir}" ""; then
            binary_path="${candidate}"
        else
            log "ERROR: fallback ${fallback_version} download failed; nothing to run"
            exit 1
        fi
    fi
fi

if [ -z "${binary_path}" ] || [ ! -x "${binary_path}" ]; then
    log "Reconciler binary is not executable: ${binary_path:-<none>}"
    exit 1
fi

# Record the binary we are about to run as the current good version, so the next
# run can fall back to it. Skip when it already IS the current target (a
# fallback run) to avoid creating a self-referential symlink.
chosen_dir="$(cd "$(dirname "${binary_path}")" && pwd -P)"
current_real="$(readlink -f "${current_link}" 2>/dev/null || true)"
if [ "${chosen_dir}" != "${current_real}" ]; then
    ln -sfn "${chosen_dir}" "${current_link}"
fi

# Drop stale cached versions now that current points at the binary we will run.
prune_cache || true

export MAGNUM_RECONCILE_MODE="${mode}"
export MAGNUM_RECONCILE_RESULT_FILE="${result_file}"
export MAGNUM_RECONCILE_LOG_FILE="${log_file}"
export MAGNUM_RECONCILE_HEAT_PARAMS_FILE="${heat_params_file}"
export MAGNUM_RECONCILE_STATE_FILE="${state_file}"
export MAGNUM_RECONCILE_RUN_STATE_FILE="${run_state_file}"
export MAGNUM_RECONCILE_STATE_BACKUP_DIR="${state_backup_dir}"
export MAGNUM_PULUMI_BACKEND_DIR="${pulumi_state_root}"
export MAGNUM_PULUMI_BACKEND_URL="file://${pulumi_state_root}"
export MAGNUM_PULUMI_BACKUP_DIR="${pulumi_backup_dir}"
export MAGNUM_RECONCILE_RUN_TIMEOUT_SECONDS="${run_timeout_seconds}"

# --- Memory governance ----------------------------------------------------
# A reconcile run drives the Pulumi engine and its pulumi-kubernetes plugin
# subprocess; on a small (2 GiB) single-master node that plugin alone can grow
# past 700 MiB and, on top of the full control plane + every cluster addon,
# OOM-kill the node mid-run (pulumi killed -> run-once exits 1 -> Heat marks the
# stack UPDATE_FAILED and the node is left wedged). Bound the Go heap of the
# reconciler AND every Go child it spawns -- the pulumi CLI and its plugins
# inherit these env vars -- so the runtime intensifies GC as the heap nears the
# limit instead of growing to the OS OOM cliff. The reconciler also auto-scales
# its --parallelism to host RAM (fewer concurrent Helm installs on small nodes),
# so this is the per-process backstop. heat-params may override either value.
mem_total_kb="$(awk '/^MemTotal:/{print $2; exit}' /proc/meminfo 2>/dev/null || true)"
if [ -n "${mem_total_kb:-}" ] && [ "${mem_total_kb}" -gt 0 ] 2>/dev/null; then
    mem_total_mib=$(( mem_total_kb / 1024 ))
    # Budget the reconciler process tree at ~45% of RAM, floored at 384 MiB and
    # capped at 4096 MiB.
    go_mem_limit_mib=$(( mem_total_mib * 45 / 100 ))
    [ "${go_mem_limit_mib}" -lt 384 ] && go_mem_limit_mib=384
    [ "${go_mem_limit_mib}" -gt 4096 ] && go_mem_limit_mib=4096
    export GOMEMLIMIT="${RECONCILER_GOMEMLIMIT:-${go_mem_limit_mib}MiB}"
    export GOGC="${RECONCILER_GOGC:-50}"
    log "Memory governance MemTotal=${mem_total_mib}MiB GOMEMLIMIT=${GOMEMLIMIT} GOGC=${GOGC}"
else
    export GOMEMLIMIT="${RECONCILER_GOMEMLIMIT:-512MiB}"
    export GOGC="${RECONCILER_GOGC:-50}"
    log "Memory governance MemTotal=unknown GOMEMLIMIT=${GOMEMLIMIT} GOGC=${GOGC}"
fi

log "Starting reconciler binary=${binary_path} mode=${mode}"
"${binary_path}" "${mode}" "$@"
rc=$?

log "Reconciler finished rc=${rc} mode=${mode}"
exit "${rc}"
EOF

$ssh_cmd mv "${launcher_path}.tmp" "${launcher_path}"
$ssh_cmd chown root:root "${launcher_path}"
$ssh_cmd chmod 755 "${launcher_path}"
