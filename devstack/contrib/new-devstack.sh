#!/bin/bash
#
# These instructions assume an Ubuntu-based host or VM for running devstack.
# Please note that if you are running this in a VM, it is vitally important
# that the underlying hardware have nested virtualization enabled or you will
# experience very poor amphora performance.
#
# Heavily based on:
# https://opendev.org/openstack/octavia/src/branch/master/devstack/contrib/new-octavia-devstack.sh

set -ex

# Set up the packages we need. Ubuntu package manager is assumed.
sudo apt-get update
sudo apt-get install git vim apparmor apparmor-utils -y

# Clone the devstack repo
sudo mkdir -p /opt/stack
if [ ! -f /opt/stack/stack.sh ]; then
    sudo chown -R ${USER}. /opt/stack
    git clone https://git.openstack.org/openstack-dev/devstack /opt/stack
fi

cat <<EOF > /opt/stack/local.conf
[[local|localrc]]
enable_plugin barbican https://opendev.org/openstack/barbican
enable_plugin heat https://opendev.org/openstack/heat
enable_plugin neutron https://opendev.org/openstack/neutron
# NOTE: you can reference your gerrit patch here
# enable_plugin magnum https://review.opendev.org/openstack/magnum refs/<etc>
enable_plugin magnum https://opendev.org/openstack/magnum
enable_plugin magnum-ui https://opendev.org/openstack/magnum-ui
enable_plugin octavia https://opendev.org/openstack/octavia
enable_plugin octavia-dashboard https://opendev.org/openstack/octavia-dashboard
LIBS_FROM_GIT+=python-octaviaclient
DATABASE_PASSWORD=secretdatabase
RABBIT_PASSWORD=secretrabbit
ADMIN_PASSWORD=secretadmin
HOST_IP=$(hostname -i)
SERVICE_PASSWORD=secretservice
SERVICE_TOKEN=111222333444
# Enable Logging
LOGFILE=/opt/stack/logs/stack.sh.log
VERBOSE=True
LOG_COLOR=True
# Octavia services
enable_service octavia o-api o-cw o-da o-hk o-hm
enable_service tempest
GLANCE_LIMIT_IMAGE_SIZE_TOTAL=10000
LIBVIRT_TYPE=kvm

[[post-config|/etc/neutron/neutron.conf]]
[DEFAULT]
advertise_mtu = True
EOF

# Fix permissions on current tty so screens can attach
sudo chmod go+rw `tty`

# Stack that stack!
/opt/stack/stack.sh

#
# Install this checkout and restart the Magnum services
#
SELF_PATH="$(realpath "${BASH_SOURCE[0]:-${(%):-%x}}")"
REPO_PATH="$(dirname "$(dirname "$(dirname "$SELF_PATH")")")"
python3 -m pip install -e "$REPO_PATH"
sudo systemctl restart devstack@magnum-api devstack@magnum-cond

source /opt/stack/openrc admin admin

pip install python-magnumclient

# Add a k8s image
curl -O https://object.arcus.openstack.hpc.cam.ac.uk/swift/v1/AUTH_f0dc9cb312144d0aa44037c9149d2513/azimuth-images-prerelease/ubuntu-focal-kube-v1.26.3-230411-1504.qcow2
openstack image create ubuntu-focal-kube-v1.26.3 \
  --file ubuntu-focal-kube-v1.26.3-230411-1504.qcow2 \
  --disk-format qcow2 \
  --container-format bare \
  --public
openstack image set ubuntu-focal-kube-v1.26.3 --os-distro ubuntu --os-version 20.04
openstack image set ubuntu-focal-kube-v1.26.3 --property kube_version=v1.26.3

# Register template for cluster api driver
openstack coe cluster template create new_driver \
  --coe kubernetes \
  --image $(openstack image show ubuntu-focal-kube-v1.26.3 -c id -f value) \
  --external-network public \
  --label kube_tag=v1.26.3 \
  --master-flavor ds2G20 \
  --flavor ds2G20 \
  --public \
  --master-lb-enabled

# You can test it like this:
#  openstack coe cluster create devstacktest \
#   --cluster-template new_driver \
#   --master-count 1 \
#   --node-count 2
#  openstack coe cluster list
#  openstack coe cluster config devstacktest
