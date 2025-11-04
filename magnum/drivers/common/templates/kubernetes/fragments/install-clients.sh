#!/bin/bash
step="install-clients"
printf "Starting to run ${step}\n"

set -e
set +x
. /etc/sysconfig/heat-params

set -x

ssh_cmd="ssh -F /srv/magnum/.ssh/config root@localhost"
mkdir -p /srv/magnum/bin/
mkdir -p /srv/magnum/k8s/

echo "PATH=/srv/magnum/bin:\$PATH" >> ~/.bashrc
echo "export HISTCONTROL=ignoredups" >> ~/.bashrc

# Download to temporary files first
$ssh_cmd curl --retry 5 --retry-delay 10 -L -o /usr/local/bin/kubelet.tmp https://cdn.dl.k8s.io/release/${KUBE_TAG}/bin/linux/${ARCH}/kubelet
$ssh_cmd curl --retry 5 --retry-delay 10 -L -o /usr/local/bin/kubectl.tmp https://cdn.dl.k8s.io/release/${KUBE_TAG}/bin/linux/${ARCH}/kubectl

# For kubelet
if ! $ssh_cmd test -f /usr/local/bin/kubelet || ! $ssh_cmd cmp -s /usr/local/bin/kubelet.tmp /usr/local/bin/kubelet; then
    $ssh_cmd mv /usr/local/bin/kubelet.tmp /usr/local/bin/kubelet
else
    $ssh_cmd rm /usr/local/bin/kubelet.tmp
fi

# For kubectl
if ! $ssh_cmd test -f /usr/local/bin/kubectl || ! $ssh_cmd cmp -s /usr/local/bin/kubectl.tmp /usr/local/bin/kubectl; then
    $ssh_cmd mv /usr/local/bin/kubectl.tmp /usr/local/bin/kubectl
else
    $ssh_cmd rm /usr/local/bin/kubectl.tmp
fi

$ssh_cmd chmod +x /usr/local/bin/kube*

if [[ "$SELINUX_MODE" == "enforcing" ]] ; then
    $ssh_cmd chcon system_u:object_r:bin_t:s0 /usr/local/bin/kube*
fi

$ssh_cmd cp /usr/local/bin/kubectl /srv/magnum/bin/
$ssh_cmd chmod +x /srv/magnum/bin/kube*

if [[ "$SELINUX_MODE" == "enforcing" ]] ; then
    $ssh_cmd chcon system_u:object_r:bin_t:s0 /srv/magnum/bin/kube*
fi

echo "INFO Installed kubernetes-server-linux."

printf "Finished running ${step}\n"
