#!/bin/bash
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

set -o errexit

source $GRENADE_DIR/grenaderc
source $GRENADE_DIR/functions

source $TOP_DIR/openrc admin admin
source $TOP_DIR/inc/ini-config

source $TARGET_RELEASE_DIR/magnum/devstack/lib/magnum

set -o xtrace

function create {
    magnum_register_image
}

function destroy {
    :
}

function _mariadb_version {
    # Use `mariadb` rather than `mysql`: mariadb.org's mariadb-client package
    # (installed by the mid-run engine bump) doesn't ship the `mysql` compat
    # symlink the distro package did, and this runs both before and after
    # that bump.
    if command -v mariadb >/dev/null 2>&1; then
        sudo mariadb -e "select version();" -sN | cut -d '-' -f 1
    else
        sudo mysql -e "select version();" -sN | cut -d '-' -f 1
    fi
}

function verify {
    local side=$1
    local db_version=$(_mariadb_version)
    if [[ "$side" == "post-upgrade" ]]; then
        if [[ "$db_version" != 11.8* ]]; then
            die $LINENO "resources.sh verify post-upgrade: expected MariaDB 11.8.x, got '$db_version'"
        fi
        echo "magnum resources verify post-upgrade: MariaDB engine confirmed at $db_version"
    else
        echo "magnum resources verify $side: MariaDB engine currently at $db_version"
    fi
}

function verify_noapi {
    echo "magnum resources verify_noapi $1: MariaDB engine currently at $(_mariadb_version)"
}

# Dispatcher
case $1 in
    "create")
        create
        ;;
    "verify")
        verify $2
        ;;
    "verify_noapi")
        verify_noapi $2
        ;;
    "destroy")
        destroy
        ;;
esac
