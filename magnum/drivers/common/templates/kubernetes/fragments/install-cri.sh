set +x

echo "START: install cri"

. /etc/sysconfig/heat-params
set -x

ssh_cmd="ssh -F /srv/magnum/.ssh/config root@localhost"

if [ "${CONTAINER_RUNTIME}" = "containerd"  ] ; then
    $ssh_cmd systemctl disable docker.service docker.socket
    $ssh_cmd systemctl stop docker.service docker.socket
    if $ssh_cmd [ -f /etc/containerd/config.toml ] ; then
        $ssh_cmd sed -i 's/bin_dir.*$/bin_dir\ =\ \""\/opt\/cni\/bin\/"\"/' /etc/containerd/config.toml
    fi
    if [ -z "${CONTAINERD_TARBALL_URL}"  ] ; then
        CONTAINERD_TARBALL_URL="https://github.com/containerd/containerd/releases/download/v${CONTAINERD_VERSION}/cri-containerd-cni-${CONTAINERD_VERSION}-linux-amd64.tar.gz"
    fi
    i=0
    until curl -o /srv/magnum/cri-containerd.tar.gz -L "${CONTAINERD_TARBALL_URL}"
    do
        i=$((i + 1))
        [ $i -lt 5 ] || break;
        sleep 5
    done

    if ! echo "${CONTAINERD_TARBALL_SHA256} /srv/magnum/cri-containerd.tar.gz" | sha256sum -c - ; then
        echo "ERROR cri-containerd.tar.gz computed checksum did NOT match, exiting."
        exit 1
    fi
    $ssh_cmd tar xzvf /srv/magnum/cri-containerd.tar.gz -C / --no-same-owner --touch --no-same-permissions
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
