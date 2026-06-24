#!/bin/sh

set -u

ssh_cmd="ssh -F /srv/magnum/.ssh/config root@localhost"
result_file="/var/lib/magnum/reconciler-last-run.json"

json_escape() {
    printf '%s' "$1" | sed ':a;N;$!ba;s/\\/\\\\/g;s/"/\\"/g;s/\r/\\r/g;s/\t/\\t/g;s/\n/\\n/g'
}

emit_heat_outputs() {
    result_json="$1"

    printf '%s' "${result_json}" | HEAT_OUTPUTS_PATH="${heat_outputs_path:-}" python -c '
import json
import os
import sys

payload = json.load(sys.stdin)
base = os.environ.get("HEAT_OUTPUTS_PATH", "")

fields = {
    "reconcile_status": payload.get("status", ""),
    "reconcile_step": payload.get("step", ""),
    "reconcile_summary": payload.get("summary", ""),
    "reconcile_reason": payload.get("reason", ""),
    "reconcile_error_code": payload.get("errorCode", ""),
}

if payload.get("status") == "failed":
    fields["reconcile_failure"] = (
        payload.get("reason") or payload.get("summary") or "reconcile failed"
    )

if base:
    for name, value in fields.items():
        path = "%s.%s" % (base, name)
        if value:
            with open(path, "w") as fh:
                fh.write(str(value))

print(payload.get("status", ""))
'
}

# Re-send the Heat completion signal from inside the heat-container-agent
# (podman --net=host), so it survives the post-reconcile egress blip.
#
# We run as the deployment's "script" hook, so /usr/bin/heat-config-notify,
# the deployed config and host egress are all available here.  The script
# hook sets heat_outputs_path to "<dir>/<deployment-id>", so its basename is
# our deployment id; the deployed config /var/lib/heat-config/deployed/<id>.json
# carries the signal credentials (deploy_auth_url / deploy_stack_id /
# deploy_resource_name ...) that heat-config-notify needs.  Best-effort: on any
# missing piece or exhausted retries we return and let the agent's one-shot
# call try (no worse than before).  Only called on success (rc == 0).
signal_heat_with_retry() {
    result_json="$1"
    notify_bin="/usr/bin/heat-config-notify"

    deploy_id=""
    if [ -n "${heat_outputs_path:-}" ]; then
        deploy_id="$(basename "${heat_outputs_path}")"
    fi
    deployed_cfg="/var/lib/heat-config/deployed/${deploy_id}.json"

    if [ -z "${deploy_id}" ] || [ ! -f "${deployed_cfg}" ] || [ ! -x "${notify_bin}" ]; then
        echo "Self-signal unavailable (deploy_id=${deploy_id}); leaving signal to agent" >&2
        return 0
    fi

    signal_data="$(printf '%s' "${result_json}" | python -c '
import json
import sys

payload = json.load(sys.stdin)
data = {
    "deploy_status_code": 0,
    "deploy_stdout": payload.get("summary", "") or payload.get("status", ""),
    "deploy_stderr": "",
    "reconcile_status": payload.get("status", ""),
    "reconcile_step": payload.get("step", ""),
    "reconcile_summary": payload.get("summary", ""),
    "reconcile_reason": payload.get("reason", ""),
    "reconcile_error_code": payload.get("errorCode", ""),
}
print(json.dumps(data))
' 2>/dev/null)"

    if [ -z "${signal_data}" ]; then
        echo "Could not build signal payload; leaving signal to agent" >&2
        return 0
    fi

    echo "Self-signalling Heat deployment ${deploy_id}" >&2
    i=0
    while [ "${i}" -lt 30 ]; do
        if printf '%s' "${signal_data}" | "${notify_bin}" "${deployed_cfg}" >/dev/null 2>&1; then
            echo "Heat signal delivered after ${i} retries" >&2
            return 0
        fi
        i=$((i + 1))
        echo "Heat signal not delivered, retry ${i}/30" >&2
        sleep 5
    done
    echo "Self-signal exhausted; falling back to agent one-shot signal" >&2
    return 0
}

# Enable the periodic timer without starting it yet.  Starting it here
# would reset OnBootSec causing an immediate timer-triggered run that
# races with the synchronous run below (double execution via flock
# serialisation).  The timer is started AFTER the synchronous run.
echo "Enabling reconciler timer (deferred start)" >&2
$ssh_cmd systemctl enable magnum-reconcile.timer 2>&1 || true

echo "Starting synchronous reconcile run" >&2

# Run the reconciler with one automatic retry.  During initial create or
# CA rotation the first attempt may fail due to transient issues (etcd
# quorum forming, API server stabilising).  A second attempt usually
# succeeds because the first run already applied most of the changes.
max_attempts=2
attempt=1
rc=1
while [ "${attempt}" -le "${max_attempts}" ]; do
    $ssh_cmd rm -f "${result_file}"
    $ssh_cmd systemctl reset-failed magnum-reconcile.service 2>/dev/null || true

    echo "Reconcile attempt ${attempt}/${max_attempts}" >&2
    $ssh_cmd systemctl start --wait magnum-reconcile.service
    rc=$?

    if [ "${rc}" -eq 0 ]; then
        break
    fi

    if [ "${attempt}" -lt "${max_attempts}" ]; then
        echo "Reconcile attempt ${attempt} failed (rc=${rc}), retrying in 15s" >&2
        sleep 15
    fi
    attempt=$((attempt + 1))
done

if $ssh_cmd test -s "${result_file}"; then
    result_json="$($ssh_cmd cat "${result_file}")"
else
    if [ "${rc}" -eq 0 ]; then
        rc=1
        summary="reconciler finished without writing result JSON"
    else
        summary="reconciler service failed before writing result JSON"
    fi

    service_log="$($ssh_cmd journalctl -u magnum-reconcile.service -n 50 --no-pager -o cat 2>/dev/null || true)"
    escaped_summary="$(json_escape "${summary}")"
    escaped_log="$(json_escape "${service_log}")"

    result_json=$(printf '{\n')
    result_json="${result_json}  \"status\": \"failed\",\n"
    result_json="${result_json}  \"step\": \"service\",\n"
    result_json="${result_json}  \"summary\": \"${escaped_summary}\",\n"
    result_json="${result_json}  \"reason\": \"${escaped_summary}\",\n"
    result_json="${result_json}  \"errorCode\": \"service_error\",\n"
    result_json="${result_json}  \"deploy_status_code\": ${rc},\n"
    result_json="${result_json}  \"deploy_stderr\": \"${escaped_log}\"\n"
    result_json="${result_json}}"
    printf '%b\n' "${result_json}" | $ssh_cmd "cat > '${result_file}.tmp' && mv '${result_file}.tmp' '${result_file}'"
fi

# Now that the synchronous run is complete, start the periodic timer.
# Use restart so a changed interval takes effect.  This is safe because
# the synchronous run already finished — no race with the timer's first tick.
echo "Starting reconciler timer" >&2
$ssh_cmd systemctl restart magnum-reconcile.timer 2>&1 || true

# Deliver the Heat completion signal ourselves, with retry, on success.
#
# After this script returns the heat-container-agent sends the Heat completion
# signal exactly ONCE (heat-config-notify) with no retry.  A CA rotation /
# upgrade restarts kube-apiserver / etcd / kube-proxy, which briefly drops this
# node's egress to the OpenStack API; if that single signal lands in the blip
# it fails ("Response None") and the SoftwareDeployment hangs in
# *_IN_PROGRESS forever even though the reconcile succeeded.  Re-invoking
# heat-config-notify in a loop rides out the blip; the agent's later one-shot
# call then becomes a harmless redundant signal.
if [ "${rc}" -eq 0 ]; then
    signal_heat_with_retry "${result_json}"
fi

printf '%b\n' "${result_json}"
if result_status="$(emit_heat_outputs "${result_json}")"; then
    :
else
    result_status=""
fi

if [ "${result_status}" = "failed" ]; then
    # Let Heat fail via SoftwareConfig error outputs so the deployment
    # reason carries the reconciler summary instead of only exit code 1.
    exit 0
fi

exit "${rc}"
