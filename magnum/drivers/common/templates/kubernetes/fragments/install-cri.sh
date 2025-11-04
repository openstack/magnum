#!/bin/bash

set +x

echo "START: install cri"

. /etc/sysconfig/heat-params
set -x

ssh_cmd="ssh -F /srv/magnum/.ssh/config root@localhost"

if [ "${CONTAINER_RUNTIME}" = "containerd"  ] ; then
   # $ssh_cmd docker network prune 2>/dev/null
    $ssh_cmd systemctl stop docker 2>/dev/null
    $ssh_cmd systemctl disable docker 2>/dev/null
   # $ssh_cmd ip link delete cni0 2>/dev/null
    if [ -z "${CONTAINERD_TARBALL_URL}"  ] ; then
        CONTAINERD_TARBALL_URL="https://github.com/containerd/containerd/releases/download/v${CONTAINERD_VERSION}/cri-containerd-cni-${CONTAINERD_VERSION}-linux-amd64.tar.gz"
    fi

    $ssh_cmd curl --retry 5 --retry-delay 10 -L ${CONTAINERD_TARBALL_URL} -o /srv/magnum/cri-containerd-cni.tar.gz
    $ssh_cmd tar xzvf /srv/magnum/cri-containerd-cni.tar.gz -C / --no-same-owner --touch --no-same-permissions --exclude=etc/cni/net.d --exclude=opt/cni/bin --exclude="*.txt" --exclude=opt/containerd/cluster/gce
    $ssh_cmd mkdir -p /etc/containerd
cat << EOF > /etc/containerd/config.toml
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
      bin_dir = "/opt/cni/bin/"
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

    $ssh_cmd systemctl daemon-reload
    $ssh_cmd systemctl enable containerd
    $ssh_cmd systemctl start containerd
else
    # CONTAINER_RUNTIME=host-docker
    $ssh_cmd systemctl disable docker
    if $ssh_cmd cat /usr/lib/systemd/system/docker.service | grep 'native.cgroupdriver'; then
            $ssh_cmd cp /usr/lib/systemd/system/docker.service /etc/systemd/system/
            sed -i "s/\(native.cgroupdriver=\)\w\+/\1$CGROUP_DRIVER/" \
                    /etc/systemd/system/docker.service
    else
            cat > /etc/systemd/system/docker.service.d/cgroupdriver.conf << EOF
    ExecStart=---exec-opt native.cgroupdriver=$CGROUP_DRIVER
EOF
    fi

    $ssh_cmd systemctl daemon-reload
    $ssh_cmd systemctl enable docker
fi

echo "END: install cri"