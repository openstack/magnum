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

export PROJECTS="openstack/barbican $PROJECTS"
export DEVSTACK_LOCAL_CONFIG="enable_plugin magnum git://git.openstack.org/openstack/magnum"
export DEVSTACK_LOCAL_CONFIG+=$'\n'"enable_plugin ceilometer git://git.openstack.org/openstack/ceilometer"

if [ "$coe" = "mesos" ]; then
    echo "MAGNUM_GUEST_IMAGE_URL="https://fedorapeople.org/groups/magnum/ubuntu-14.04.3-mesos-0.25.0.qcow2"" >> $BASE/new/devstack/localrc
fi

$BASE/new/devstack-gate/devstack-vm-gate.sh
