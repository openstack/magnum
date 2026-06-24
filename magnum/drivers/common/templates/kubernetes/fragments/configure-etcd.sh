#!/bin/sh

. /etc/sysconfig/heat-params

set -x

is_true() {
    [ "$(echo "${1:-false}" | tr '[:upper:]' '[:lower:]')" = "true" ]
}

# During a pure CA rotation the certificates have already been replaced
# and etcd has been restarted by rotate-kubernetes-ca-certs-master.sh.
# Re-running the full cluster-join / membership logic with mixed old/new
# certs across the rolling batch can break the etcd cluster (the LB may
# route to a not-yet-rotated member whose certs no longer verify against
# the new CA, causing cleanup_etcd to destroy a healthy node).
if [ -n "${CA_ROTATION_ID:-}" ] && \
   ! is_true "${IS_UPGRADE:-false}" && \
   ! is_true "${IS_RESIZE:-false}"; then
    echo "Pure CA rotation detected – skipping etcd reconfiguration"
else

ssh_cmd="ssh -F /srv/magnum/.ssh/config root@localhost"

# Export proxy variables if set
[ -n "$HTTP_PROXY" ] && export HTTP_PROXY
[ -n "$HTTPS_PROXY" ] && export HTTPS_PROXY
[ -n "$NO_PROXY" ] && export NO_PROXY

# Set protocol and cert directory
cert_dir="/etc/etcd/certs"
protocol="https"
[ "$TLS_DISABLED" = "True" ] && protocol="http"

# Get local IP address
if [ -z "$KUBE_NODE_IP" ]; then
    # FIXME: Set KUBE_NODE_IP correctly
    KUBE_NODE_IP=$(curl -s http://169.254.169.254/latest/meta-data/local-ipv4)
fi
myip="${KUBE_NODE_IP}"

# -------------------------------------------------------
# Volume preparation
# -------------------------------------------------------
if [ -n "$ETCD_VOLUME_SIZE" ] && [ "$ETCD_VOLUME_SIZE" -gt 0 ]; then
    if ! $ssh_cmd mountpoint -q /var/lib/etcd; then
        attempts=60
        while [ ${attempts} -gt 0 ]; do
            device_name=$($ssh_cmd ls /dev/disk/by-id | grep ${ETCD_VOLUME:0:20}$)
            [ -n "$device_name" ] && break
            echo "waiting for disk device"
            sleep 0.5
            $ssh_cmd udevadm trigger
            let attempts--
        done

        if [ -z "$device_name" ]; then
            echo "ERROR: disk device does not exist" >&2
            exit 1
        fi

        device_path=/dev/disk/by-id/${device_name}
        fstype=$($ssh_cmd blkid -s TYPE -o value ${device_path} || echo "")
        [ "$fstype" != "xfs" ] && $ssh_cmd mkfs.xfs -f ${device_path}
        $ssh_cmd mkdir -p /var/lib/etcd
        if ! grep -q "${device_path} /var/lib/etcd" /etc/fstab; then
            echo "${device_path} /var/lib/etcd xfs defaults 0 0" >> /etc/fstab
        fi
        $ssh_cmd mount -a
        $ssh_cmd chown -R etcd.etcd /var/lib/etcd
        $ssh_cmd chmod 755 /var/lib/etcd
    fi
fi

# -------------------------------------------------------
# Service creation section
# -------------------------------------------------------
if [ "$(echo $USE_PODMAN | tr '[:upper:]' '[:lower:]')" = "true" ]; then
    service_file="/etc/systemd/system/etcd.service"
    container_image="${CONTAINER_INFRA_PREFIX:-"quay.io/coreos/"}etcd"
    if [[ "$container_image" != *"/"* ]]; then
        container_image="docker.io/library/$container_image"
    fi
    service_content=$(cat << EOF
[Unit]
Description=Etcd server
After=network-online.target
Wants=network-online.target

[Service]
EnvironmentFile=/etc/sysconfig/heat-params
ExecStartPre=mkdir -p /var/lib/etcd
ExecStartPre=-/bin/podman rm etcd
ExecStart=/bin/podman run \
    --name etcd \
    --volume /etc/pki/ca-trust/extracted/pem:/etc/ssl/certs:ro,z \
    --volume /etc/etcd:/etc/etcd:ro,z \
    --volume /var/lib/etcd:/var/lib/etcd:rshared,z \
    --net=host \
    ${container_image}:${ETCD_TAG} \
    /usr/local/bin/etcd \
    --config-file /etc/etcd/etcd.conf.yaml
ExecStop=/bin/podman stop etcd
TimeoutStartSec=10min
IOSchedulingClass=best-effort
IOSchedulingPriority=0
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
)
    if [ ! -f "$service_file" ] || [ "$(cat $service_file)" != "$service_content" ]; then
        echo "$service_content" > "$service_file"
        $ssh_cmd systemctl daemon-reload
    fi
else
    _prefix=${CONTAINER_INFRA_PREFIX:-"docker.io/openstackmagnum/"}
    if ! $ssh_cmd atomic images list | grep -q "^${_prefix}etcd:${ETCD_TAG}"; then
        $ssh_cmd atomic install --system-package no --system --storage ostree --name=etcd ${_prefix}etcd:${ETCD_TAG}
    fi
fi

# -------------------------------------------------------
# etcdctl installation
# -------------------------------------------------------
etcdctl_dir="/usr/local/bin"
etcd_download_path="/srv/magnum/etcd"
$ssh_cmd mkdir -p ${etcd_download_path}
ETCD_VERSION=${ETCD_TAG#v}
etcd_tgz="${etcd_download_path}/etcd-v${ETCD_VERSION}-linux-amd64.tar.gz"
if [ ! -f "${etcd_tgz}" ] || ! $ssh_cmd etcdctl version 2>/dev/null | grep -q "etcdctl version: ${ETCD_VERSION}"; then
    $ssh_cmd curl --retry 5 --retry-delay 10 -L \
        https://github.com/etcd-io/etcd/releases/download/v${ETCD_VERSION}/etcd-v${ETCD_VERSION}-linux-amd64.tar.gz \
        -o "${etcd_tgz}.tmp"
    $ssh_cmd mv "${etcd_tgz}.tmp" "${etcd_tgz}"
    $ssh_cmd mkdir -p ${etcd_download_path}/tmp
    $ssh_cmd tar -C ${etcd_download_path}/tmp -xzf ${etcd_tgz}
    $ssh_cmd cp ${etcd_download_path}/tmp/etcd-v${ETCD_VERSION}-linux-amd64/etcdctl ${etcdctl_dir}/
    $ssh_cmd chmod +x ${etcdctl_dir}/etcdctl
    $ssh_cmd rm -rf ${etcd_download_path}/tmp
fi

# -------------------------------------------------------
# Helper functions
# -------------------------------------------------------

run_etcdctl() {
    local endpoints="$1"
    shift
    local max_attempts=3
    local attempt=1
    local delay=3
    local timeout=5
    local etcdctl_opts=(
        "--endpoints=$endpoints"
        "--command-timeout=${timeout}s"
    )
    if [ "$TLS_DISABLED" != "True" ]; then
        etcdctl_opts+=(
            --cacert="$cert_dir/ca.crt"
            --cert="$cert_dir/server.crt"
            --key="$cert_dir/server.key"
        )
    fi
    while [ ${attempt} -le ${max_attempts} ]; do
        echo "Attempt $attempt/$max_attempts: etcdctl $*" >&2
        if output=$($ssh_cmd ETCDCTL_API=3 ${etcdctl_dir}/etcdctl "${etcdctl_opts[@]}" "$@" 2>&1); then
            echo "$output"
            return 0
        fi
        echo "$output" >&2
        sleep $delay
        let attempt++
    done
    return 1
}

# Checks if our node is already a member using LB endpoint
is_member() {
    local endpoints="$1"
    local node_name="$2"
    local node_ip="$3"
    member_list=$(run_etcdctl "$endpoints" member list) || return 1
    echo "$member_list" | grep -q -E "$node_name|$node_ip" || return 1
    return 0
}

# Build complete etcd configuration including TLS and proxy settings.
# "new" mode uses the discovery URL; "existing" mode uses the initial_cluster string.
build_complete_config() {
    local mode="$1"
    local extra="${2:-}"
    
    # Start with base configuration
    if [ "$mode" = "new" ]; then
        cat << EOF
name: "$INSTANCE_NAME"
data-dir: "/var/lib/etcd/default.etcd"
listen-metrics-urls: "http://$myip:2378"
listen-client-urls: "$protocol://$myip:2379,http://127.0.0.1:2379"
listen-peer-urls: "$protocol://$myip:2380"
advertise-client-urls: "$protocol://$myip:2379"
initial-advertise-peer-urls: "$protocol://$myip:2380"
discovery: "$ETCD_DISCOVERY_URL"
heartbeat-interval: 1000
election-timeout: 15000
auto-compaction-mode: periodic
auto-compaction-retention: "24h"
EOF
    elif [ "$mode" = "new-static" ]; then
        # Discovery-free bootstrap of a brand-new cluster from a known member
        # list. A shared initial-cluster-token makes all members agree they
        # belong to the same cluster.
        cat << EOF
name: "$INSTANCE_NAME"
data-dir: "/var/lib/etcd/default.etcd"
listen-metrics-urls: "http://$myip:2378"
listen-client-urls: "$protocol://$myip:2379,http://127.0.0.1:2379"
listen-peer-urls: "$protocol://$myip:2380"
advertise-client-urls: "$protocol://$myip:2379"
initial-advertise-peer-urls: "$protocol://$myip:2380"
initial-cluster: "$extra"
initial-cluster-state: "new"
initial-cluster-token: "$(etcd_cluster_token)"
heartbeat-interval: 1000
election-timeout: 15000
auto-compaction-mode: periodic
auto-compaction-retention: "24h"
EOF
    elif [ "$mode" = "existing" ]; then
        cat << EOF
name: "$INSTANCE_NAME"
data-dir: "/var/lib/etcd/default.etcd"
listen-metrics-urls: "http://$myip:2378"
listen-client-urls: "$protocol://$myip:2379,http://127.0.0.1:2379"
listen-peer-urls: "$protocol://$myip:2380"
advertise-client-urls: "$protocol://$myip:2379"
initial-advertise-peer-urls: "$protocol://$myip:2380"
initial-cluster: "$extra"
initial-cluster-state: "existing"
heartbeat-interval: 1000
election-timeout: 15000
auto-compaction-mode: periodic
auto-compaction-retention: "24h"
EOF
    fi
    
    # Add TLS configuration if enabled
    if [ "$TLS_DISABLED" = "False" ]; then
        cat << EOF
client-transport-security:
  cert-file: "$cert_dir/server.crt"
  key-file: "$cert_dir/server.key"
  client-cert-auth: true
  trusted-ca-file: "$cert_dir/ca.crt"
peer-transport-security:
  cert-file: "$cert_dir/server.crt"
  key-file: "$cert_dir/server.key"
  client-cert-auth: true
  trusted-ca-file: "$cert_dir/ca.crt"
EOF
    fi
    
    # Add HTTP proxy configuration if set
    if [ -n "$HTTP_PROXY" ]; then
        cat << EOF
# HTTP proxy to use for traffic to discovery service.
discovery-proxy: $HTTP_PROXY
EOF
    fi
}

# Legacy function for compatibility (now calls the complete config builder)
build_config() {
    build_complete_config "$@"
}

# Cluster-wide token so every member of a freshly bootstrapped static cluster
# agrees it belongs to the same cluster.
etcd_cluster_token() {
    if [ -n "${CLUSTER_UUID:-}" ]; then
        echo "etcd-${CLUSTER_UUID}"
    else
        echo "magnum-etcd-cluster"
    fi
}

# True when this node is the first/only master (the bootstrapper). Matches the
# reconciler's IsFirstMaster: instance name ending in "master-0", or a
# single-master cluster.
is_first_master() {
    case "$INSTANCE_NAME" in
        *master-0) return 0 ;;
    esac
    [ "${NUMBER_OF_MASTERS:-1}" = "1" ]
}

# Echo the static etcd initial-cluster member list used to bootstrap a NEW
# cluster without v2 discovery, and return 0 if one could be determined.
# ETCD_INITIAL_CLUSTER (full "name=peerURL,..." list) wins; otherwise a
# first/single master bootstraps a one-node cluster from its own peer URL.
static_initial_cluster() {
    if [ -n "${ETCD_INITIAL_CLUSTER:-}" ]; then
        echo "$ETCD_INITIAL_CLUSTER"
        return 0
    fi
    if is_first_master; then
        echo "$INSTANCE_NAME=$protocol://$myip:2380"
        return 0
    fi
    return 1
}

# Bootstrap a brand-new etcd cluster from the static member list. Exits non-zero
# when no list can be determined (multi-master with neither ETCD_INITIAL_CLUSTER
# nor an existing cluster to join — bootstrapping self would split-brain).
bootstrap_static_cluster() {
    local members
    if ! members=$(static_initial_cluster); then
        echo "Error: no healthy LB endpoint, no discovery URL, and cannot determine a static initial-cluster (multi-master needs ETCD_INITIAL_CLUSTER or an existing cluster to join)." >&2
        return 1
    fi
    echo "Bootstrapping new etcd cluster from static initial-cluster: $members" >&2
    cleanup_etcd
    config=$(build_config new-static "$members")
    write_and_start_etcd "$config"
}

# Remove our node from LB (if present) and add it back.
rejoin_cluster() {
    echo "Rejoining cluster via LB endpoint $lb_endpoint" >&2
    member_id=$(run_etcdctl "$lb_endpoint" member list | grep -E "$INSTANCE_NAME|$myip" | cut -d',' -f1)
    [ -n "$member_id" ] && run_etcdctl "$lb_endpoint" member remove "$member_id" || true
    if add_output=$(run_etcdctl "$lb_endpoint" member add "$INSTANCE_NAME" --peer-urls="$protocol://$myip:2380"); then
        initial_cluster=$(echo "$add_output" | grep '^ETCD_INITIAL_CLUSTER=' | cut -d'=' -f2- | tr -d '"')
        config=$(build_config existing "$initial_cluster")
        write_and_start_etcd "$config"
        etcd_restart_needed=0  # Reset flag since we just restarted via write_and_start_etcd
        return 0
    else
        echo "Failed to rejoin cluster via LB" >&2
        return 1
    fi
}

# Join a new node to an existing cluster.
join_existing_cluster() {
    echo "Joining new node to existing cluster via LB endpoint $lb_endpoint" >&2
    if add_output=$(run_etcdctl "$lb_endpoint" member add "$INSTANCE_NAME" --peer-urls="$protocol://$myip:2380"); then
        initial_cluster=$(echo "$add_output" | grep '^ETCD_INITIAL_CLUSTER=' | cut -d'=' -f2- | tr -d '"')
        config=$(build_config existing "$initial_cluster")
        write_and_start_etcd "$config"
        etcd_restart_needed=0  # Reset flag since we just restarted via write_and_start_etcd
        return 0
    else
        echo "Failed to join existing cluster via LB" >&2
        return 1
    fi
}

# Remove excess members during scale-down operations.
# This should only run on master-0 when the target master count is less than current members.
cleanup_excess_members() {
    # Only run on master-0
    if ! echo "$INSTANCE_NAME" | grep -q "master-0$"; then
        echo "Not master-0, skipping member cleanup" >&2
        return 0
    fi
    
    # Only proceed if we have a target master count
    if [ -z "$NUMBER_OF_MASTERS" ] || [ "$NUMBER_OF_MASTERS" -eq 0 ]; then
        echo "No target master count specified, skipping member cleanup" >&2
        return 0
    fi
    
    # Only proceed if LB is available
    if [ $lb_ok -eq 0 ]; then
        echo "LB not available, skipping member cleanup" >&2
        return 0
    fi
    
    echo "Checking if member cleanup is needed (target: $NUMBER_OF_MASTERS masters)" >&2
    echo "Note: For etcd quorum safety during scale-down, only 1 master will be removed per operation" >&2
    
    # Get current member list
    if ! member_list=$(run_etcdctl "$lb_endpoint" member list 2>/dev/null); then
        echo "Failed to get member list, skipping cleanup" >&2
        return 0
    fi
    
    # Count current master members (assume all etcd members are masters)
    current_count=$(echo "$member_list" | wc -l)
    echo "Current etcd members: $current_count, target: $NUMBER_OF_MASTERS" >&2
    
    # If current count is not greater than target, no cleanup needed
    if [ "$current_count" -le "$NUMBER_OF_MASTERS" ]; then
        echo "No excess members to remove" >&2
        return 0
    fi
    
    # Calculate how many to remove
    to_remove=$((current_count - NUMBER_OF_MASTERS))
    echo "Need to remove $to_remove excess members" >&2
    
    # Safety: Only remove 1 member at a time to maintain etcd quorum during scale-down
    if [ "$to_remove" -gt 1 ]; then
        echo "Limiting removal to 1 member at a time for etcd quorum safety during scale-down" >&2
        echo "Additional scale-down operations will be needed to reach the target count" >&2
        to_remove=1
    fi
    
    # Additional safety: Ensure we don't remove all members
    remaining_after_removal=$((current_count - to_remove))
    if [ "$remaining_after_removal" -lt 1 ]; then
        echo "Cannot remove member: would leave cluster with $remaining_after_removal members" >&2
        return 0
    fi
    
    # Get member names and IDs, sort by name to remove highest numbered masters first
    members_to_remove=$(echo "$member_list" | \
        grep -E "master-[0-9]+|$myip" | \
        grep -v "$INSTANCE_NAME" | \
        sort -t'-' -k2 -nr | \
        head -n "$to_remove")
    
    if [ -z "$members_to_remove" ]; then
        echo "No suitable members found for removal" >&2
        return 0
    fi
    
    # Remove each excess member
    echo "$members_to_remove" | while read member_info; do
        if [ -n "$member_info" ]; then
            member_id=$(echo "$member_info" | cut -d',' -f1)
            member_name=$(echo "$member_info" | cut -d',' -f3 | tr -d ' ')
            echo "Removing excess member: $member_name (ID: $member_id)" >&2
            
            if run_etcdctl "$lb_endpoint" member remove "$member_id"; then
                echo "Successfully removed member $member_name" >&2
            else
                echo "Failed to remove member $member_name" >&2
            fi
        fi
    done
    
    echo "Member cleanup completed" >&2
}

# Clean up etcd data and stop service.
cleanup_etcd() {
    echo "Cleaning up etcd data..." >&2
    $ssh_cmd systemctl stop etcd
    $ssh_cmd podman rm -f etcd || true
    sleep 5
    echo "Etcd cleanup completed" >&2
}

# Check if the discovery URL is valid and contains cluster data.
check_discovery_url() {
    local url="$1"
    if [ -n "$url" ]; then
        local data
        data=$(curl -sf "$url") || true
        if [ -n "$data" ] && ! echo "$data" | grep -q "unable to GET token"; then
            if echo "$data" | grep -q '"nodes":\['; then
                echo "Discovery URL contains existing cluster data" >&2
                return 0
            elif echo "$data" | jq -e '.node.nodes' >/dev/null 2>&1; then
                echo "Discovery URL contains existing cluster data" >&2
                return 0
            elif echo "$data" | grep -q '"dir":true'; then
                echo "Discovery URL is valid but empty, can be used for new cluster" >&2
                return 0
            fi
        fi
    fi
    echo "Discovery URL is not valid or contains no cluster data" >&2
    return 1
}

# Write etcd configuration and start the service.
write_and_start_etcd() {
    local config_content="$1"
    $ssh_cmd mkdir -p /etc/etcd
    echo "$config_content" > /etc/etcd/etcd.conf.yaml
    if [ ! -f /etc/etcd/etcd.conf.yaml ]; then
        echo "Failed to write etcd config file" >&2
        ETCD_WRITE_RESULT=1
    else
        echo "Starting etcd service..." >&2
        $ssh_cmd systemctl daemon-reload
        $ssh_cmd systemctl restart etcd
        ETCD_WRITE_RESULT=0
        etcd_restart_needed=0  # Reset flag since we just restarted
    fi
}

# Rebuild complete configuration for existing healthy nodes
rebuild_config_if_needed() {
    if [ ! -f /etc/etcd/etcd.conf.yaml ]; then
        echo "No existing etcd config found, skipping rebuild" >&2
        return 0
    fi
    
    # Check if we need to add missing TLS or proxy configuration
    needs_tls=0
    needs_proxy=0
    
    if [ "$TLS_DISABLED" = "False" ] && ! grep -q "client-transport-security" /etc/etcd/etcd.conf.yaml 2>/dev/null; then
        needs_tls=1
    fi
    
    if [ -n "$HTTP_PROXY" ] && ! grep -q "discovery-proxy" /etc/etcd/etcd.conf.yaml 2>/dev/null; then
        needs_proxy=1
    fi
    
    if [ $needs_tls -eq 1 ] || [ $needs_proxy -eq 1 ]; then
        echo "Rebuilding etcd configuration to add missing TLS/proxy settings" >&2
        
        # Extract current cluster configuration from existing config
        existing_config=$(cat /etc/etcd/etcd.conf.yaml)
        
        if echo "$existing_config" | grep -q "^discovery:"; then
            # Node uses discovery URL
            discovery_url=$(echo "$existing_config" | grep "^discovery:" | cut -d' ' -f2 | tr -d '"')
            ETCD_DISCOVERY_URL="$discovery_url"
            new_config=$(build_complete_config "new")
        elif echo "$existing_config" | grep -q "^initial-cluster:"; then
            # Node uses initial-cluster
            initial_cluster=$(echo "$existing_config" | grep "^initial-cluster:" | cut -d' ' -f2- | tr -d '"')
            new_config=$(build_complete_config "existing" "$initial_cluster")
        else
            echo "Could not determine cluster configuration type, skipping rebuild" >&2
            return 0
        fi
        
        # Write the new complete configuration
        echo "$new_config" > /etc/etcd/etcd.conf.yaml
        etcd_restart_needed=1
        echo "Configuration rebuilt with complete TLS/proxy settings" >&2
    else
        echo "Configuration is already complete, no rebuild needed" >&2
    fi
}

# -------------------------------------------------------
# Resize operation handling
# -------------------------------------------------------
if [ "${IS_RESIZE:-false}" = "True" ]; then
    echo "Resize operation detected. Running member cleanup only." >&2
    
    # Set up required variables for cleanup function
    local_endpoint="$protocol://$myip:2379"
    lb_endpoint="$protocol://$ETCD_LB_VIP:2379"
    
    # Check LB VIP response for cleanup function
    if run_etcdctl "$lb_endpoint" endpoint health >/dev/null 2>&1; then
        lb_ok=1
    else
        lb_ok=0
    fi
    
    # For resize operations, we only need to clean up excess members
    # but skip cluster join/creation logic to avoid stale discovery URL issues
    cleanup_excess_members
    
    echo "Resize operation completed." >&2
else
    # -------------------------------------------------------
    # Cluster Join/Creation Logic with Added Membership Check
    # -------------------------------------------------------

    # Flag to track if etcd restart is needed
    etcd_restart_needed=0

    # Define key endpoints.
    local_endpoint="$protocol://$myip:2379"
    lb_endpoint="$protocol://$ETCD_LB_VIP:2379"

    # Initialize flags.
    discovery_ok=0
    lb_ok=0
    local_ok=0

# Check discovery URL.
if check_discovery_url "$ETCD_DISCOVERY_URL"; then
    discovery_ok=1
fi

# Check LB VIP response.
if run_etcdctl "$lb_endpoint" endpoint health >/dev/null 2>&1; then
    lb_ok=1
fi

# Check local endpoint health.
if run_etcdctl "$local_endpoint" endpoint health >/dev/null 2>&1; then
    local_ok=1
fi

echo "Discovery OK: $discovery_ok, LB OK: $lb_ok, Local OK: $local_ok" >&2

# Decision tree:
# 1. If discovery URL is valid:
#    a. If LB is available, check membership.
#       - If our node is present in LB member list:
#           * If local endpoint is unhealthy → trigger rejoin.
#           * Otherwise → skip join/creation.
#       - If our node is NOT present:
#           * If LB has an existing cluster → join existing cluster.
#           * Otherwise → create new cluster using discovery URL.
#    b. If LB is not available → create new cluster using discovery URL.
#
# 2. If discovery URL is not valid:
#    a. If LB is available:
#       - If our node is a member:
#           * If local endpoint is unhealthy → trigger rejoin.
#           * Otherwise → skip join/creation.
#       - If our node is NOT a member → join existing cluster.
#    b. Else, error out.
if [ $discovery_ok -eq 1 ]; then
    if [ $lb_ok -eq 1 ]; then
        if is_member "$lb_endpoint" "$INSTANCE_NAME" "$myip"; then
            echo "Discovery valid and LB shows our node as a member." >&2
            if [ $local_ok -eq 0 ]; then
                echo "Local endpoint is unhealthy. Triggering rejoin." >&2
                rejoin_cluster || exit 1
            else
                echo "Local endpoint is healthy. Skipping join/creation logic." >&2
                # Check if we need to rebuild config for TLS/proxy settings
                rebuild_config_if_needed
            fi
        else
            # Check if LB has an existing cluster (has other members)
            if existing_members=$(run_etcdctl "$lb_endpoint" member list 2>/dev/null) && [ -n "$existing_members" ]; then
                echo "Discovery valid but LB shows existing cluster without our node. Joining existing cluster." >&2
                cleanup_etcd
                join_existing_cluster || exit 1
            else
                echo "Discovery valid and no existing cluster. Creating new cluster using discovery URL." >&2
                cleanup_etcd
                config=$(build_config new)
                write_and_start_etcd "$config"
            fi
        fi
    else
        echo "LB not available but discovery URL is valid. Creating new cluster using discovery URL." >&2
        cleanup_etcd
        config=$(build_config new)
        write_and_start_etcd "$config"
    fi
elif [ $discovery_ok -eq 0 ]; then
    if [ $lb_ok -eq 1 ]; then
        if is_member "$lb_endpoint" "$INSTANCE_NAME" "$myip"; then
            echo "Discovery invalid but LB shows our node as a member." >&2
            if [ $local_ok -eq 0 ]; then
                echo "Local endpoint is unhealthy. Triggering rejoin." >&2
                rejoin_cluster || exit 1
            else
                echo "Local endpoint is healthy. Skipping join/creation logic." >&2
                # Check if we need to rebuild config for TLS/proxy settings
                rebuild_config_if_needed
            fi
        else
            # LB up but we are not a member: join if a cluster already exists,
            # otherwise bootstrap a new cluster statically (no discovery).
            if existing_members=$(run_etcdctl "$lb_endpoint" member list 2>/dev/null) && [ -n "$existing_members" ]; then
                echo "Discovery invalid but LB shows existing cluster without our node. Joining existing cluster." >&2
                cleanup_etcd
                join_existing_cluster || exit 1
            else
                echo "Discovery invalid and LB has no existing cluster. Bootstrapping new cluster statically." >&2
                bootstrap_static_cluster || exit 1
            fi
        fi
    elif [ $local_ok -eq 1 ]; then
        # Local etcd is healthy but not visible via the LB (single-node cluster,
        # or LB down). Treat as an existing standalone node; never re-bootstrap.
        echo "Discovery invalid and LB unavailable, but local etcd is healthy. Rebuilding config if needed." >&2
        rebuild_config_if_needed
    else
        # No discovery, no LB cluster, no local etcd: bootstrap statically.
        echo "No discovery URL and no healthy LB endpoint. Bootstrapping new cluster statically." >&2
        bootstrap_static_cluster || exit 1
    fi
fi

# -------------------------------------------------------
# TLS and Proxy Configuration
# -------------------------------------------------------
# NOTE: TLS and proxy configuration are now handled within build_complete_config()
# and rebuild_config_if_needed() functions to avoid duplicate configuration entries.

# -------------------------------------------------------
# Final etcd restart (only if needed)
# -------------------------------------------------------
if [ $etcd_restart_needed -eq 1 ]; then
    echo "Restarting etcd service due to configuration changes" >&2
    $ssh_cmd systemctl daemon-reload
    $ssh_cmd systemctl restart etcd
    echo "Etcd restart completed" >&2
else
    echo "No configuration changes detected, skipping etcd restart" >&2
    # Still reload daemon in case systemd service file changed
    $ssh_cmd systemctl daemon-reload
fi
fi
fi
