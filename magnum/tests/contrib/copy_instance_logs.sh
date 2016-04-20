#!/usr/bin/env bash
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

# Save trace setting
XTRACE=$(set +o | grep xtrace)
set -o xtrace

echo "Magnum's copy_instance_logs.sh was called..."

SSH_IP=$1
COE=${2-kubernetes}
NODE_TYPE=${3-master}
LOG_PATH=/opt/stack/logs/bay-nodes/${NODE_TYPE}-${SSH_IP}
KEYPAIR=${4-default}
PRIVATE_KEY=

echo "If private key is specified, save to temp and use that; else, use default"
if [[ "$KEYPAIR" == "default" ]]; then
    PRIVATE_KEY=$(readlink -f ~/.ssh/id_rsa)
else
    PRIVATE_KEY="$(mktemp id_rsa.$SSH_IP.XXX)"
    echo -en "$KEYPAIR" > $PRIVATE_KEY
fi

function remote_exec {
    local ssh_user=$1
    local cmd=$2
    local logfile=${LOG_PATH}/$3
    ssh -i $PRIVATE_KEY -o StrictHostKeyChecking=no ${ssh_user}@${SSH_IP} "${cmd}" > ${logfile} 2>&1
}

mkdir -p $LOG_PATH

if [[ "$COE" == "kubernetes" ]]; then
    SSH_USER=minion
    remote_exec $SSH_USER "sudo systemctl --full list-units --no-pager" systemctl_list_units.log
    remote_exec $SSH_USER "sudo journalctl -u cloud-config --no-pager" cloud-config.log
    remote_exec $SSH_USER "sudo journalctl -u cloud-final --no-pager" cloud-final.log
    remote_exec $SSH_USER "sudo journalctl -u cloud-init-local --no-pager" cloud-init-local.log
    remote_exec $SSH_USER "sudo journalctl -u cloud-init --no-pager" cloud-init.log
    remote_exec $SSH_USER "sudo cat /var/log/cloud-init-output.log" cloud-init-output.log
    remote_exec $SSH_USER "sudo journalctl -u kubelet --no-pager" kubelet.log
    remote_exec $SSH_USER "sudo journalctl -u kube-proxy --no-pager" kube-proxy.log
    remote_exec $SSH_USER "sudo journalctl -u etcd --no-pager" etcd.log
    remote_exec $SSH_USER "sudo journalctl -u kube-apiserver --no-pager" kube-apiserver.log
    remote_exec $SSH_USER "sudo journalctl -u kube-scheduler --no-pager" kube-scheduler.log
    remote_exec $SSH_USER "sudo journalctl -u kube-controller-manager --no-pager" kube-controller-manager.log
    remote_exec $SSH_USER "sudo journalctl -u docker-storage-setup --no-pager" docker-storage-setup.log
    remote_exec $SSH_USER "sudo systemctl status docker-storage-setup -l" docker-storage-setup.service.status.log
    remote_exec $SSH_USER "sudo systemctl show docker-storage-setup --no-pager" docker-storage-setup.service.show.log
    remote_exec $SSH_USER "sudo cat /etc/sysconfig/docker-storage-setup 2>/dev/null" docker-storage-setup.sysconfig.env.log
    remote_exec $SSH_USER "sudo journalctl -u docker --no-pager" docker.log
    remote_exec $SSH_USER "sudo systemctl status docker -l" docker.service.status.log
    remote_exec $SSH_USER "sudo systemctl show docker --no-pager" docker.service.show.log
    remote_exec $SSH_USER "sudo cat /etc/sysconfig/docker" docker.sysconfig.env.log
    remote_exec $SSH_USER "sudo cat /etc/sysconfig/docker-storage" docker-storage.sysconfig.env.log
    remote_exec $SSH_USER "sudo cat /etc/sysconfig/docker-network" docker-network.sysconfig.env.log
    remote_exec $SSH_USER "sudo timeout 60s docker ps --all=true --no-trunc=true" docker-containers.log
    remote_exec $SSH_USER "sudo tar zcvf - /var/lib/docker/containers 2>/dev/null" docker-container-configs.tar.gz
    remote_exec $SSH_USER "sudo journalctl -u flanneld --no-pager" flanneld.log
    remote_exec $SSH_USER "sudo ip a" ipa.log
    remote_exec $SSH_USER "sudo netstat -an" netstat.log
    remote_exec $SSH_USER "sudo df -h" dfh.log
    remote_exec $SSH_USER "sudo journalctl -u wc-notify --no-pager" wc-notify.log
    remote_exec $SSH_USER "cat /etc/sysconfig/heat-params" heat-params
elif [[ "$COE" == "swarm" ]]; then
    SSH_USER=fedora
    remote_exec $SSH_USER "sudo systemctl --full list-units --no-pager" systemctl_list_units.log
    remote_exec $SSH_USER "sudo journalctl -u cloud-config --no-pager" cloud-config.log
    remote_exec $SSH_USER "sudo journalctl -u cloud-final --no-pager" cloud-final.log
    remote_exec $SSH_USER "sudo journalctl -u cloud-init-local --no-pager" cloud-init-local.log
    remote_exec $SSH_USER "sudo journalctl -u cloud-init --no-pager" cloud-init.log
    remote_exec $SSH_USER "sudo journalctl -u etcd --no-pager" etcd.log
    remote_exec $SSH_USER "sudo journalctl -u swarm-manager --no-pager" swarm-manager.log
    remote_exec $SSH_USER "sudo journalctl -u swarm-agent --no-pager" swarm-agent.log
    remote_exec $SSH_USER "sudo journalctl -u docker-storage-setup --no-pager" docker-storage-setup.log
    remote_exec $SSH_USER "sudo systemctl status docker-storage-setup -l" docker-storage-setup.service.status.log
    remote_exec $SSH_USER "sudo systemctl show docker-storage-setup --no-pager" docker-storage-setup.service.show.log
    remote_exec $SSH_USER "sudo cat /etc/sysconfig/docker-storage-setup 2>/dev/null" docker-storage-setup.sysconfig.env.log
    remote_exec $SSH_USER "sudo journalctl -u docker --no-pager" docker.log
    remote_exec $SSH_USER "sudo systemctl status docker -l" docker.service.status.log
    remote_exec $SSH_USER "sudo systemctl show docker --no-pager" docker.service.show.log
    remote_exec $SSH_USER "sudo cat /etc/sysconfig/docker" docker.sysconfig.env.log
    remote_exec $SSH_USER "sudo cat /etc/sysconfig/docker-storage" docker-storage.sysconfig.env.log
    remote_exec $SSH_USER "sudo cat /etc/sysconfig/docker-network" docker-network.sysconfig.env.log
    remote_exec $SSH_USER "sudo timeout 60s docker ps --all=true --no-trunc=true" docker-containers.log
    remote_exec $SSH_USER "sudo tar zcvf - /var/lib/docker/containers 2>/dev/null" docker-container-configs.tar.gz
    remote_exec $SSH_USER "sudo journalctl -u flanneld --no-pager" flanneld.log
    remote_exec $SSH_USER "sudo ip a" ipa.log
    remote_exec $SSH_USER "sudo netstat -an" netstat.log
    remote_exec $SSH_USER "sudo df -h" dfh.log
    remote_exec $SSH_USER "cat /etc/sysconfig/heat-params" heat-params
else
    echo "ERROR: Unknown COE '${COE}'"
    EXIT_CODE=1
fi

# Restore xtrace
$XTRACE

exit $EXIT_CODE
