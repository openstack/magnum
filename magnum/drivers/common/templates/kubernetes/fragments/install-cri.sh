#!/bin/bash

set +x

echo "START: install cri"

. /etc/sysconfig/heat-params
set -x

ssh_cmd="ssh -F /srv/magnum/.ssh/config root@localhost"

is_true() {
    [ "$(echo "${1:-false}" | tr '[:upper:]' '[:lower:]')" = "true" ]
}

is_pure_ca_rotation() {
    [ -n "${CA_ROTATION_ID:-}" ] && \
    ! is_true "${IS_UPGRADE:-false}" && \
    ! is_true "${IS_RESIZE:-false}"
}

containerd_already_configured() {
    $ssh_cmd test -f /etc/containerd/config.toml || return 1
    $ssh_cmd "grep -Fq 'bin_dir = \"/opt/cni/bin\"' /etc/containerd/config.toml" || return 1
    $ssh_cmd systemctl list-unit-files containerd.service >/dev/null 2>&1 || return 1
}

if is_pure_ca_rotation; then
    echo "END: install cri"
else
    if [ "${CONTAINER_RUNTIME}" = "containerd"  ] ; then
        if ! is_true "${IS_UPGRADE:-false}" && ! is_true "${IS_RESIZE:-false}" && \
           containerd_already_configured; then
            echo "containerd already configured, skipping CRI install"
        else
           # $ssh_cmd docker network prune 2>/dev/null
            $ssh_cmd systemctl stop docker 2>/dev/null
            $ssh_cmd systemctl disable docker 2>/dev/null
           # $ssh_cmd ip link delete cni0 2>/dev/null
            if [ -z "${CONTAINERD_TARBALL_URL}"  ] ; then
                CONTAINERD_TARBALL_URL="https://github.com/containerd/containerd/releases/download/v${CONTAINERD_VERSION}/cri-containerd-cni-${CONTAINERD_VERSION}-linux-amd64.tar.gz"
            fi

            $ssh_cmd curl --retry 5 --retry-delay 10 -L ${CONTAINERD_TARBALL_URL} -o /srv/magnum/cri-containerd-cni.tar.gz
            $ssh_cmd rm -f /etc/containerd/config.toml /etc/containerd/config.toml.magnum.tmp
            $ssh_cmd tar xzvf /srv/magnum/cri-containerd-cni.tar.gz -C / --no-same-owner --touch --no-same-permissions --exclude=etc/cni/net.d --exclude=etc/containerd/config.toml --exclude=opt/cni/bin --exclude="*.txt" --exclude=opt/containerd/cluster/gce
            $ssh_cmd mkdir -p /etc/containerd /opt/cni/bin
cat << EOF | $ssh_cmd tee /etc/containerd/config.toml.magnum.tmp >/dev/null
version = 2
root = "/var/lib/containerd"
state = "/run/containerd"
oom_score = 0

[grpc]
  address = "/run/containerd/containerd.sock"
  max_recv_message_size = 16777216
  max_send_message_size = 16777216

[debug]
  level = "info"

[metrics]
  address = ""
  grpc_histogram = false

[plugins]
  [plugins."io.containerd.grpc.v1.cri"]
    sandbox_image = "registry.k8s.io/pause:3.9"
    max_container_log_line_size = 16384
    enable_unprivileged_ports = true
    enable_unprivileged_icmp = true
    [plugins."io.containerd.grpc.v1.cri".cni]
      bin_dir = "/opt/cni/bin"
      conf_dir = "/etc/cni/net.d"
    [plugins."io.containerd.grpc.v1.cri".containerd]
      default_runtime_name = "runc"
      snapshotter = "overlayfs"
    [plugins."io.containerd.grpc.v1.cri".registry]
      [plugins."io.containerd.grpc.v1.cri".registry.mirrors]
        [plugins."io.containerd.grpc.v1.cri".registry.mirrors."docker.io"]
          endpoint = ["https://registry-1.docker.io"]
  [plugins."io.containerd.internal.v1.opt"]
    path = "/var/lib/containerd/opt"
EOF

            $ssh_cmd mv /etc/containerd/config.toml.magnum.tmp /etc/containerd/config.toml
            if ! $ssh_cmd "grep -Fq 'bin_dir = \"/opt/cni/bin\"' /etc/containerd/config.toml"; then
                echo "Failed to write containerd config with /opt/cni/bin"
                exit 1
            fi

            $ssh_cmd systemctl daemon-reload
            $ssh_cmd systemctl enable containerd
            $ssh_cmd systemctl start containerd
        fi
    else
        # CONTAINER_RUNTIME=host-docker
        $ssh_cmd systemctl disable docker
        if $ssh_cmd cat /usr/lib/systemd/system/docker.service | grep 'native.cgroupdriver'; then
                $ssh_cmd cp /usr/lib/systemd/system/docker.service /etc/systemd/system/
                $ssh_cmd sed -i "s/\(native.cgroupdriver=\)\w\+/\1$CGROUP_DRIVER/" \
                        /etc/systemd/system/docker.service
        else
                $ssh_cmd mkdir -p /etc/systemd/system/docker.service.d
                cat << EOF | $ssh_cmd tee /etc/systemd/system/docker.service.d/cgroupdriver.conf >/dev/null
    ExecStart=---exec-opt native.cgroupdriver=$CGROUP_DRIVER
EOF
        fi

        $ssh_cmd systemctl daemon-reload
        $ssh_cmd systemctl enable docker
    fi
fi

echo "END: install cri"
