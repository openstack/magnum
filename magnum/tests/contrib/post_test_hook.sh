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

# This script is executed inside post_test_hook function in devstack gate.

# Sleep some time until all services are starting
sleep 5

if ! function_exists echo_summary; then
    function echo_summary {
        echo $@
    }
fi

# Save trace setting
XTRACE=$(set +o | grep xtrace)
set -o xtrace

echo_summary "magnum's post_test_hook.sh was called..."
(set -o posix; set)

sudo pip install -r test-requirements.txt

# Get admin credentials
pushd ../devstack
source openrc admin admin
popd

# First we test Magnum's command line to see if we can stand up
# a baymodel, bay and a pod
export NIC_ID=$(neutron net-show public | awk '/ id /{print $4}')
export IMAGE_ID=$(glance image-show fedora-21-atomic-2 | awk '/ id /{print $4}')

echo_summary "Running magnum-template-manage"
magnum-template-manage list-templates

echo_summary "Generate a key-pair"
nova keypair-add default

echo_summary "Running baymodel-create"
magnum baymodel-create --name default --keypair-id default \
    --external-network-id $NIC_ID \
    --image-id $IMAGE_ID \
    --flavor-id m1.small --docker-volume-size 5

echo_summary "Running baymodel-list"
magnum baymodel-list
export BAYMODEL_ID=$(magnum baymodel-list | awk '/ default /{print $2}')

echo_summary "Running bay-create"
magnum bay-create --name k8s --baymodel $BAYMODEL_ID

echo_summary "Running bay-list"
magnum bay-list
export BAY_ID=$(magnum bay-list | awk '/ k8s /{print $2}')

echo_summary "Running bay-delete"
magnum bay-delete $BAY_ID

echo_summary "Running baymodel-delete"
magnum baymodel-delete $BAY_ID

echo_summary "Running keypair-delete"
nova keypair-delete default

# Run functional tests
echo "Running magnum functional test suite"
sudo -E -H -u stack tox -e functional
EXIT_CODE=$?

# Save the logs
sudo mv ../logs/* /opt/stack/logs/

# Restore xtrace
$XTRACE

exit $EXIT_CODE
