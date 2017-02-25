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
export DEVSTACK_LOCAL_CONFIG="enable_plugin heat git://git.openstack.org/openstack/heat"

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

if [ "$coe" = "mesos" ]; then
    export DEVSTACK_LOCAL_CONFIG+=$'\n'"MAGNUM_GUEST_IMAGE_URL=https://tarballs.openstack.org/magnum/images/ubuntu-mesos.qcow2"
elif [ "$coe" = "k8s-coreos" ]; then
    export DEVSTACK_LOCAL_CONFIG+=$'\n'"MAGNUM_GUEST_IMAGE_URL=http://beta.release.core-os.net/amd64-usr/current/coreos_production_openstack_image.img.bz2"
elif [ "${coe}${special}" = "k8s-ironic" ]; then
    export DEVSTACK_LOCAL_CONFIG+=$'\n'"MAGNUM_GUEST_IMAGE_URL='https://fedorapeople.org/groups/magnum/fedora-25-kubernetes-ironic.tar.gz'"
    export DEVSTACK_LOCAL_CONFIG+=$'\n'"MAGNUM_IMAGE_NAME='fedora-25-kubernetes-ironic'"

    export DEVSTACK_GATE_VIRT_DRIVER="ironic"
    # NOTE(yuanying): Current implementation requires only 1 subnet under network
    export DEVSTACK_LOCAL_CONFIG+=$'\n'"IP_VERSION=4"
    # NOTE(strigazi) keep cinder
    # export DEVSTACK_LOCAL_CONFIG+=$'\n'"disable_service cinder c-sch c-api c-vol"

    export DEVSTACK_LOCAL_CONFIG+=$'\n'"enable_plugin ironic git://git.openstack.org/openstack/ironic"

    export DEVSTACK_LOCAL_CONFIG+=$'\n'"IRONIC_DEPLOY_DRIVER=pxe_ssh"
    export DEVSTACK_LOCAL_CONFIG+=$'\n'"IRONIC_BAREMETAL_BASIC_OPS=True"
    export DEVSTACK_LOCAL_CONFIG+=$'\n'"IRONIC_VM_LOG_DIR=/opt/stack/new/ironic-bm-logs"
    export DEVSTACK_LOCAL_CONFIG+=$'\n'"DEFAULT_INSTANCE_TYPE=baremetal"
    export DEVSTACK_LOCAL_CONFIG+=$'\n'"BUILD_TIMEOUT=600"
    export DEVSTACK_LOCAL_CONFIG+=$'\n'"IRONIC_CALLBACK_TIMEOUT=600"
    export DEVSTACK_LOCAL_CONFIG+=$'\n'"Q_AGENT=openvswitch"
    export DEVSTACK_LOCAL_CONFIG+=$'\n'"Q_ML2_TENANT_NETWORK_TYPE=vxlan"
    export DEVSTACK_LOCAL_CONFIG+=$'\n'"IRONIC_BUILD_DEPLOY_RAMDISK=False"

    export DEVSTACK_LOCAL_CONFIG+=$'\n'"SWIFT_ENABLE_TEMPURLS=True"
    export DEVSTACK_LOCAL_CONFIG+=$'\n'"SWIFT_TEMPURL_KEY=password"
    export DEVSTACK_LOCAL_CONFIG+=$'\n'"SWIFT_HASH=password"

    export DEVSTACK_LOCAL_CONFIG+=$'\n'"IRONIC_ENABLED_DRIVERS=fake,agent_ssh,agent_ipmitool,pxe_ssh,pxe_ipmitool"
    export DEVSTACK_LOCAL_CONFIG+=$'\n'"VOLUME_BACKING_FILE_SIZE=24G"
    export DEVSTACK_LOCAL_CONFIG+=$'\n'"FORCE_CONFIG_DRIVE=True"
    export DEVSTACK_LOCAL_CONFIG+=$'\n'"IRONIC_DEPLOY_DRIVER_ISCSI_WITH_IPA=True"
    export DEVSTACK_LOCAL_CONFIG+=$'\n'"IRONIC_RAMDISK_TYPE=tinyipa"
    export DEVSTACK_LOCAL_CONFIG+=$'\n'"IRONIC_IPXE_ENABLED=True"
    export DEVSTACK_LOCAL_CONFIG+=$'\n'"IRONIC_VM_COUNT=2"
    export DEVSTACK_LOCAL_CONFIG+=$'\n'"IRONIC_VM_SSH_PORT=22"
    export DEVSTACK_LOCAL_CONFIG+=$'\n'"IRONIC_VM_SPECS_RAM=1024"
    export DEVSTACK_LOCAL_CONFIG+=$'\n'"IRONIC_VM_SPECS_DISK=10"
    export DEVSTACK_LOCAL_CONFIG+=$'\n'"IRONIC_VM_EPHEMERAL_DISK=5"
else
    export DEVSTACK_LOCAL_CONFIG+=$'\n'"MAGNUM_GUEST_IMAGE_URL='https://fedorapeople.org/groups/magnum/fedora-atomic-25-latest.qcow2'"
    export DEVSTACK_LOCAL_CONFIG+=$'\n'"MAGNUM_IMAGE_NAME='fedora-atomic-25-latest'"
fi

# Enable magnum plugin in the last step
export DEVSTACK_LOCAL_CONFIG+=$'\n'"enable_plugin magnum git://git.openstack.org/openstack/magnum"

$BASE/new/devstack-gate/devstack-vm-gate.sh
