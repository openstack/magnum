#!/usr/bin/env bash

# ``shutdown-magnum``

set -o errexit

source $GRENADE_DIR/grenaderc
source $GRENADE_DIR/functions

# We need base DevStack functions for this
source $BASE_DEVSTACK_DIR/functions
source $BASE_DEVSTACK_DIR/stackrc # needed for status directory
source $BASE_DEVSTACK_DIR/lib/tls
source $BASE_DEVSTACK_DIR/lib/apache

source $BASE_RELEASE_DIR/magnum/devstack/settings
source $BASE_RELEASE_DIR/magnum/devstack/lib/magnum

set -o xtrace

stop_magnum

# Make sure the services are really gone, otherwise start_magnum in
# upgrade.sh is a no-op and the old code keeps serving requests
ensure_services_stopped magnum-api magnum-cond
