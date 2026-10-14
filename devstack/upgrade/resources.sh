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
    force_stray_collation
}

function destroy {
    :
}

# Parse $MAGNUM_CONF's [database]/connection URL into
# MAGNUM_DB_USER / MAGNUM_DB_PASS / MAGNUM_DB_HOST / MAGNUM_DB_NAME.
# Returns 1 (and leaves those unset) on non-mysql backends (sqlite,
# postgresql), so callers can skip collation handling entirely.
function get_magnum_db_creds {
    local conn
    conn=$(iniget $MAGNUM_CONF database connection)
    [[ "$conn" == mysql* ]] || return 1

    local creds=${conn#*://}
    local hostdb=${creds#*@}
    local userpass=${creds%%@*}
    MAGNUM_DB_USER=${userpass%%:*}
    MAGNUM_DB_PASS=${userpass#*:}
    MAGNUM_DB_HOST=${hostdb%%/*}
    MAGNUM_DB_NAME=${hostdb#*/}
    MAGNUM_DB_NAME=${MAGNUM_DB_NAME%%\?*}
}

# Run a query against the magnum database using the creds parsed by
# get_magnum_db_creds.
function magnum_db_query {
    mysql -u"$MAGNUM_DB_USER" -p"$MAGNUM_DB_PASS" -h"$MAGNUM_DB_HOST" \
        -N -B -e "$1" "$MAGNUM_DB_NAME"
}

# Forge a stray collation on `nodegroup` relative to `cluster`'s actual
# live collation on the base/old release's database, before any upgrade
# migrations run.
#
# This job's nodeset installs a stock MariaDB (bumped mid-run to 11.8 by
# upgrade.sh, but the base side still stacks on the distro default), and
# since ca853f59 no magnum migration declares an explicit charset any
# more -- so every table on a fresh devstack install consistently
# inherits the database's own default collation and the stray-collation
# condition bug 2121797 depends on can never arise naturally here. Force
# the mismatch so the post-upgrade verify (and the corrective migration
# it is meant to exercise) actually has something real to catch/fix,
# instead of trivially observing that nothing was ever wrong.
function force_stray_collation {
    get_magnum_db_creds || return 0

    local cluster_collation
    cluster_collation=$(magnum_db_query \
        "SELECT TABLE_COLLATION FROM information_schema.tables \
            WHERE TABLE_SCHEMA='$MAGNUM_DB_NAME' AND TABLE_NAME='cluster';")
    [[ -n "$cluster_collation" ]] || die $LINENO \
        "Could not read cluster table's collation to forge a mismatch from"

    local charset=${cluster_collation%%_*}
    local forged_collation
    forged_collation=$(magnum_db_query \
        "SELECT COLLATION_NAME FROM information_schema.collations \
            WHERE CHARACTER_SET_NAME='$charset' \
            AND COLLATION_NAME != '$cluster_collation' LIMIT 1;")
    [[ -n "$forged_collation" ]] || die $LINENO \
        "No alternate $charset collation available to forge a mismatch with"

    magnum_db_query \
        "ALTER TABLE nodegroup CONVERT TO CHARACTER SET $charset \
            COLLATE $forged_collation;"

    # Sanity-check the forgery actually landed, so a silent ALTER
    # failure doesn't degrade this back into an unintentional no-op.
    local nodegroup_collation
    nodegroup_collation=$(magnum_db_query \
        "SELECT TABLE_COLLATION FROM information_schema.tables \
            WHERE TABLE_SCHEMA='$MAGNUM_DB_NAME' AND TABLE_NAME='nodegroup';")
    [[ "$nodegroup_collation" != "$cluster_collation" ]] || die $LINENO \
        "Failed to forge a stray collation on nodegroup before upgrade"
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

# Fail if the magnum database ends up with tables on more than one
# collation. A mismatch here reproduces "Illegal mix of collations" on
# joins such as nodegroup.cluster_id = cluster.uuid; see bug 2121797.
# Only meaningful once the post-upgrade migrations have run.
function _check_table_collations {
    get_magnum_db_creds || return 0
    local rows=$(magnum_db_query \
        "SELECT TABLE_NAME, TABLE_COLLATION FROM information_schema.tables \
            WHERE TABLE_SCHEMA='$MAGNUM_DB_NAME' AND TABLE_TYPE='BASE TABLE';")
    echo "$rows"
    local distinct=$(echo "$rows" | awk -F'\t' '{print $2}' | sort -u | wc -l)
    if [[ $distinct -gt 1 ]]; then
        die $LINENO "Stray table collation(s) detected in the magnum database"
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
        _check_table_collations
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
        verify "$2"
        ;;
    "verify_noapi")
        verify_noapi "$2"
        ;;
    "destroy")
        destroy
        ;;
esac
