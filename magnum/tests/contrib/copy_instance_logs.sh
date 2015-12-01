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

function remote_exec {
    local ssh_user=$1
    local cmd=$2
    local logfile=${LOG_PATH}/$3
    ssh -o StrictHostKeyChecking=no ${ssh_user}@${SSH_IP} "${cmd}" > ${logfile} 2>&1
}

mkdir -p $LOG_PATH

if [[ "$COE" == "kubernetes" ]]; then
    SSH_USER=minion
    remote_exec $SSH_USER "sudo systemctl --full list-units" systemctl_list_units.log
    remote_exec $SSH_USER "sudo journalctl -u cloud-config --no-pager" cloud-config.log
    remote_exec $SSH_USER "sudo journalctl -u cloud-final --no-pager" cloud-final.log
    remote_exec $SSH_USER "sudo journalctl -u cloud-init-local --no-pager" cloud-init-local.log
    remote_exec $SSH_USER "sudo journalctl -u cloud-init --no-pager" cloud-init.log
    remote_exec $SSH_USER "sudo journalctl -u kubelet --no-pager" kubelet.log
    remote_exec $SSH_USER "sudo journalctl -u kube-proxy --no-pager" kube-proxy.log
    remote_exec $SSH_USER "sudo journalctl -u etcd --no-pager" etcd.log
    remote_exec $SSH_USER "sudo journalctl -u kube-apiserver --no-pager" kube-apiserver.log
    remote_exec $SSH_USER "sudo journalctl -u kube-scheduler --no-pager" kube-scheduler.log
    remote_exec $SSH_USER "sudo journalctl -u kube-controller-manager --no-pager" kube-controller-manager.log
    remote_exec $SSH_USER "sudo journalctl -u docker --no-pager" docker.log
    remote_exec $SSH_USER "sudo journalctl -u flanneld --no-pager" flanneld.log
    remote_exec $SSH_USER "sudo ip a" ipa.log
    remote_exec $SSH_USER "sudo netstat -an" netstat.log
elif [[ "$COE" == "swarm" ]]; then
    SSH_USER=fedora
    remote_exec $SSH_USER "sudo systemctl --full list-units" systemctl_list_units.log
    remote_exec $SSH_USER "sudo journalctl -u cloud-config --no-pager" cloud-config.log
    remote_exec $SSH_USER "sudo journalctl -u cloud-final --no-pager" cloud-final.log
    remote_exec $SSH_USER "sudo journalctl -u cloud-init-local --no-pager" cloud-init-local.log
    remote_exec $SSH_USER "sudo journalctl -u cloud-init --no-pager" cloud-init.log
    remote_exec $SSH_USER "sudo journalctl -u etcd --no-pager" etcd.log
    remote_exec $SSH_USER "sudo journalctl -u swarm-manager --no-pager" swarm-manager.log
    remote_exec $SSH_USER "sudo journalctl -u swarm-agent --no-pager" swarm-agent.log
    remote_exec $SSH_USER "sudo journalctl -u docker --no-pager" docker.log
    remote_exec $SSH_USER "sudo journalctl -u flanneld --no-pager" flanneld.log
    remote_exec $SSH_USER "sudo ip a" ipa.log
    remote_exec $SSH_USER "sudo netstat -an" netstat.log
else
    echo "ERROR: Unknown COE '${COE}'"
    EXIT_CODE=1
fi

# Restore xtrace
$XTRACE

exit $EXIT_CODE
