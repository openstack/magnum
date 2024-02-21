#!/bin/bash -x
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
#
# This script is executed inside gate_hook function in devstack gate.


coe=$1
special=$2

export PROJECTS="openstack/barbican $PROJECTS"
export DEVSTACK_LOCAL_CONFIG="enable_plugin heat https://git.openstack.org/openstack/heat"

export DEVSTACK_LOCAL_CONFIG+=$'\n'"disable_service horizon"
export DEVSTACK_LOCAL_CONFIG+=$'\n'"disable_service s-account"
export DEVSTACK_LOCAL_CONFIG+=$'\n'"disable_service s-container"
export DEVSTACK_LOCAL_CONFIG+=$'\n'"disable_service s-object"
export DEVSTACK_LOCAL_CONFIG+=$'\n'"disable_service s-proxy"
export DEVSTACK_LOCAL_CONFIG+=$'\n'"disable_service ceilometer-acentral"
export DEVSTACK_LOCAL_CONFIG+=$'\n'"disable_service ceilometer-acompute"
export DEVSTACK_LOCAL_CONFIG+=$'\n'"disable_service ceilometer-alarm-evaluator"
export DEVSTACK_LOCAL_CONFIG+=$'\n'"disable_service ceilometer-alarm-notifier"
export DEVSTACK_LOCAL_CONFIG+=$'\n'"disable_service ceilometer-api"
export DEVSTACK_LOCAL_CONFIG+=$'\n'"disable_service ceilometer-collector"

if egrep --quiet '(vmx|svm)' /proc/cpuinfo; then
    export DEVSTACK_GATE_LIBVIRT_TYPE=kvm
fi

if [[ -e /etc/ci/mirror_info.sh ]]; then
    source /etc/ci/mirror_info.sh
fi

# Enable magnum plugin in the last step
export DEVSTACK_LOCAL_CONFIG+=$'\n'"enable_plugin magnum https://git.openstack.org/openstack/magnum"

$BASE/new/devstack-gate/devstack-vm-gate.sh
