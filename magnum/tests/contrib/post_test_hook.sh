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

# Set up all necessary test data
function create_test_data {
    # First we test Magnum's command line to see if we can stand up
    # a baymodel, bay and a pod

    coe=$1
    local image_name="fedora-21-atomic"
    if [ $coe == 'mesos' ]; then
        image_name="ubuntu-14.04"
    fi
    export NIC_ID=$(neutron net-show public | awk '/ id /{print $4}')
    export IMAGE_ID=$(glance --os-image-api-version 1 image-list | grep $image_name | awk '{print $2}')

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
copy_logs = true
EOF

    # Note(eliqiao): Let's keep this only for debugging on gate.
    echo_summary $CREDS_FILE
    cat $CREDS_FILE

    # Create a keypair for use in the functional tests.
    echo_summary "Generate a key-pair"
    ssh-keygen -t rsa -N "" -f ~/.ssh/id_rsa
    nova keypair-add  --pub-key ~/.ssh/id_rsa.pub default

}

function add_flavor {
    # because of policy.json change in nova, flavor-create is now an admin-only feature
    # moving this out to only be used by admins

    # Get admin credentials
    pushd ../devstack
    source openrc admin admin
    # NOTE(hongbin): This is a temporary work around. These variables are for
    # keystone v3, but magnum is using v2 API. Therefore, unset them to make the
    # keystoneclient work.
    # Bug: #1473600
    unset OS_PROJECT_DOMAIN_ID
    unset OS_USER_DOMAIN_ID
    unset OS_AUTH_TYPE
    popd

    # Due to keystone defaulting everything to v3, we need to update to make func tests
    # work in our gates back to v2
    export OS_AUTH_URL=http://127.0.0.1:5000/v2.0
    export OS_IDENTITY_API_VERSION=2.0

    # Create magnum specific flavor for use in functional tests.
    echo_summary "Create a flavor"
    nova flavor-create  m1.magnum 100 1024 8 1
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

constraints="-c $REQUIREMENTS_DIR/upper-constraints.txt"
sudo pip install $constraints -U -r requirements.txt -r test-requirements.txt

export MAGNUM_DIR="$BASE/new/magnum"
sudo chown -R jenkins:stack $MAGNUM_DIR

# Run functional tests
# Currently we support functional-api, functional-k8s, will support swarm,
# mesos later.

echo "Running magnum functional test suite for $1"

# For api, we will run tempest tests

coe=$1

if [[ "api" == "$coe" ]]; then
    # Import devstack functions 'iniset', 'iniget' and 'trueorfalse'
    source $BASE/new/devstack/functions
    echo "TEMPEST_SERVICES+=,magnum" >> $localrc_path
    pushd $BASE/new/tempest
    sudo chown -R jenkins:stack $BASE/new/tempest

    add_flavor

    # Set demo credentials
    source $BASE/new/devstack/accrc/demo/demo
    unset OS_AUTH_TYPE

    create_test_data $coe

    # Set up tempest config with magnum goodness
    iniset $BASE/new/tempest/etc/tempest.conf magnum image_id $IMAGE_ID
    iniset $BASE/new/tempest/etc/tempest.conf magnum nic_id $NIC_ID
    iniset $BASE/new/tempest/etc/tempest.conf magnum keypair_id default
    iniset $BASE/new/tempest/etc/tempest.conf magnum flavor_id m1.magnum

    # show tempest config with magnum
    cat etc/tempest.conf

    # Set up concurrency and test regex
    export MAGNUM_TEMPEST_CONCURRENCY=${MAGNUM_TEMPEST_CONCURRENCY:-1}
    export MAGNUM_TESTS=${MAGNUM_TESTS:-'magnum.tests.functional.api.v1'}

    echo "Running tempest magnum test suites"
    sudo -H -u jenkins tox -eall-plugin -- $MAGNUM_TESTS --concurrency=$MAGNUM_TEMPEST_CONCURRENCY
else
    # Get admin credentials
    pushd ../devstack
    source openrc admin admin
    # NOTE(hongbin): This is a temporary work around. These variables are for
    # keystone v3, but magnum is using v2 API. Therefore, unset them to make the
    # keystoneclient work.
    # Bug: #1473600
    unset OS_PROJECT_DOMAIN_ID
    unset OS_USER_DOMAIN_ID
    unset OS_AUTH_TYPE
    popd

    add_flavor

    create_test_data $coe

    sudo -E -H -u jenkins tox -e functional-"$coe" -- --concurrency=1
fi
EXIT_CODE=$?

# Delete the keypair used in the functional test.
echo_summary "Running keypair-delete"
nova keypair-delete default

# Delete the flavor used in the functional test.
echo_summary "Running flavor-delete"
nova flavor-delete m1.magnum

# Save functional testing log
sudo cp $MAGNUM_DIR/functional-tests.log /opt/stack/logs/

# Save functional_creds.conf
sudo cp $CREDS_FILE /opt/stack/logs/

# Save the logs
sudo mv ../logs/* /opt/stack/logs/

# Restore xtrace
$XTRACE

exit $EXIT_CODE
