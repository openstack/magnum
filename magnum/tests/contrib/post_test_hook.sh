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

# Check if a function already exists
function function_exists {
    declare -f -F $1 > /dev/null
}

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

if [[ "$USE_CONSTRAINTS" == "True" ]]; then
    constraints="-c $REQUIREMENTS_DIR/upper-constraints.txt"
else
    constraints=""
fi
# XXX(lifeless) This should probably use setup_dev or some such.
sudo pip install $constraints -U -r requirements.txt -r test-requirements.txt

export MAGNUM_DIR="$BASE/new/magnum"
sudo chown -R jenkins:stack $MAGNUM_DIR

# Get admin credentials
pushd ../devstack
source openrc admin admin
# NOTE(hongbin): This is a temporary work around. These variables are for
# keystone v3, but magnum is using v2 API. Therefore, unset them to make the
# keystoneclient work.
# Bug: #1473600
unset OS_PROJECT_DOMAIN_ID
unset OS_USER_DOMAIN_ID
popd

# First we test Magnum's command line to see if we can stand up
# a baymodel, bay and a pod
export NIC_ID=$(neutron net-show public | awk '/ id /{print $4}')
export IMAGE_ID=$(glance --os-image-api-version 1 image-show fedora-21-atomic-5 | awk '/ id /{print $4}')


# pass the appropriate variables via a config file
CREDS_FILE=$MAGNUM_DIR/functional_creds.conf
cat <<EOF > $CREDS_FILE
# Credentials for functional testing

[auth]
auth_url = $OS_AUTH_URL
magnum_url = $BYPASS_URL
username = $OS_USERNAME
tenant_name = $OS_TENANT_NAME
password = $OS_PASSWORD
auth_version = v2
[admin]
user = $OS_USERNAME
tenant = $OS_TENANT_NAME
pass = $OS_PASSWORD
region_name = $OS_REGION_NAME
[magnum]
image_id = $IMAGE_ID
nic_id = $NIC_ID
keypair_id = default
flavor_id = m1.magnum
EOF

# Create a keypair for use in the functional tests.
echo_summary "Generate a key-pair"
nova keypair-add default

# Create magnum specific flavor for use in functional tests.
echo_summary "Create a flavor"
nova flavor-create  m1.magnum 100 2048 8 1

# Run functional tests
echo "Running magnum functional test suite"
sudo -E -H -u jenkins tox -e functional -- --concurrency=1
EXIT_CODE=$?

# Delete the keypair used in the functional test.
echo_summary "Running keypair-delete"
nova keypair-delete default

# Delete the flavor used in the functional test.
echo_summary "Running flavor-delete"
nova flavor-delete m1.magnum

# Save the logs
sudo mv ../logs/* /opt/stack/logs/

# Restore xtrace
$XTRACE

exit $EXIT_CODE
