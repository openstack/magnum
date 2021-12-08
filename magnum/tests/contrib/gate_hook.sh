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

if [ "$coe" = "k8s-coreos" ]; then
    export DEVSTACK_LOCAL_CONFIG+=$'\n'"MAGNUM_GUEST_IMAGE_URL=http://beta.release.core-os.net/amd64-usr/current/coreos_production_openstack_image.img.bz2"
elif [ "${coe}${special}" = "k8s-ironic" ]; then
    export DEVSTACK_LOCAL_CONFIG+=$'\n'"MAGNUM_GUEST_IMAGE_URL='https://fedorapeople.org/groups/magnum/fedora-kubernetes-ironic-latest.tar.gz'"
    export DEVSTACK_LOCAL_CONFIG+=$'\n'"MAGNUM_IMAGE_NAME='fedora-kubernetes-ironic-latest'"

    export DEVSTACK_GATE_VIRT_DRIVER="ironic"
    # NOTE(strigazi) keep cinder
    # export DEVSTACK_LOCAL_CONFIG+=$'\n'"disable_service cinder c-sch c-api c-vol"

    export DEVSTACK_LOCAL_CONFIG+=$'\n'"enable_plugin ironic https://git.openstack.org/openstack/ironic"

    # NOTE(TheJulia): Ironic switched to "hardware types" in Queens and
    # removed legacy "drivers" in Rocky. "ipmi" superceeds *_ipmitool drivers.
    export DEVSTACK_LOCAL_CONFIG+=$'\n'"IRONIC_DEPLOY_DRIVER=ipmi"
    # NOTE(ykarel) Ironic to work with magnum, requires devstack to be configured with IP_VERSION=4
    export DEVSTACK_LOCAL_CONFIG+=$'\n'"IP_VERSION=4"
    export DEVSTACK_LOCAL_CONFIG+=$'\n'"IRONIC_BAREMETAL_BASIC_OPS=True"
    export DEVSTACK_LOCAL_CONFIG+=$'\n'"IRONIC_VM_LOG_DIR=/opt/stack/new/ironic-bm-logs"
    export DEVSTACK_LOCAL_CONFIG+=$'\n'"DEFAULT_INSTANCE_TYPE=baremetal"
    export DEVSTACK_LOCAL_CONFIG+=$'\n'"BUILD_TIMEOUT=600"
    export DEVSTACK_LOCAL_CONFIG+=$'\n'"IRONIC_CALLBACK_TIMEOUT=600"
    export DEVSTACK_LOCAL_CONFIG+=$'\n'"Q_AGENT=openvswitch"
    export DEVSTACK_LOCAL_CONFIG+=$'\n'"Q_ML2_TENANT_NETWORK_TYPE=vxlan"
    export DEVSTACK_LOCAL_CONFIG+=$'\n'"IRONIC_BUILD_DEPLOY_RAMDISK=False"

    # We don't enable swift in Gate Jobs so not required
    # export DEVSTACK_LOCAL_CONFIG+=$'\n'"SWIFT_ENABLE_TEMPURLS=True"
    # export DEVSTACK_LOCAL_CONFIG+=$'\n'"SWIFT_TEMPURL_KEY=password"
    # export DEVSTACK_LOCAL_CONFIG+=$'\n'"SWIFT_HASH=password"
    # NOTE(TheJulia): Enable interface order will result in the iscsi
    # deployment method being used by default.
    export DEVSTACK_LOCAL_CONFIG+=$'\n'"IRONIC_ENABLED_DEPLOY_INTERFACES=iscsi,direct"
    export DEVSTACK_LOCAL_CONFIG+=$'\n'"VOLUME_BACKING_FILE_SIZE=24G"
    export DEVSTACK_LOCAL_CONFIG+=$'\n'"FORCE_CONFIG_DRIVE=True"
    export DEVSTACK_LOCAL_CONFIG+=$'\n'"IRONIC_RAMDISK_TYPE=tinyipa"
    export DEVSTACK_LOCAL_CONFIG+=$'\n'"IRONIC_IPXE_ENABLED=False"
    export DEVSTACK_LOCAL_CONFIG+=$'\n'"IRONIC_VM_COUNT=2"
    export DEVSTACK_LOCAL_CONFIG+=$'\n'"IRONIC_VM_SSH_PORT=22"
    export DEVSTACK_LOCAL_CONFIG+=$'\n'"IRONIC_VM_SPECS_RAM=1024"
    export DEVSTACK_LOCAL_CONFIG+=$'\n'"IRONIC_VM_SPECS_DISK=10"
    export DEVSTACK_LOCAL_CONFIG+=$'\n'"IRONIC_VM_EPHEMERAL_DISK=5"
else
    export DEVSTACK_LOCAL_CONFIG+=$'\n'"MAGNUM_GUEST_IMAGE_URL='https://builds.coreos.fedoraproject.org/prod/streams/stable/builds/35.20220116.3.0/x86_64/fedora-coreos-35.20220116.3.0-openstack.x86_64.qcow2.xz'"
    export DEVSTACK_LOCAL_CONFIG+=$'\n'"MAGNUM_IMAGE_NAME='fedora-coreos-35.20220116.3.0-openstack.x86_64'"
fi

# Enable magnum plugin in the last step
export DEVSTACK_LOCAL_CONFIG+=$'\n'"enable_plugin magnum https://git.openstack.org/openstack/magnum"

$BASE/new/devstack-gate/devstack-vm-gate.sh
