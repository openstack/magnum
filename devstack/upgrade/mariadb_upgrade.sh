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
#
# Upgrades the MariaDB database engine itself (not an OpenStack service)
# partway through the magnum-grenade run. This lives here, bolted onto
# magnum's own grenade upgrade hooks, because grenade has no mechanism to
# register an independent "upgrade the database server" project:
# register_project_for_upgrade resolves a project's script directory from
# the caller's own devstack/upgrade/settings location, and grenade's plugin
# loader only ever looks for that file at one fixed path per required
# project. There is no upstream "mariadb" grenade plugin to hang this off
# of instead. This file is only ever sourced from devstack/upgrade/upgrade.sh
# after $TARGET_DEVSTACK_DIR/stackrc has already been sourced.

MARIADB_TARGET_SERIES="11.8"

function upgrade_mariadb_engine {
    if [[ "$MYSQL_SERVICE_NAME" != "mariadb" ]]; then
        die $LINENO "upgrade_mariadb_engine: expected MYSQL_SERVICE_NAME=mariadb, got '$MYSQL_SERVICE_NAME'"
    fi

    curl -LsS https://downloads.mariadb.com/MariaDB/mariadb_repo_setup -o $SAVE_DIR/mariadb_repo_setup
    sudo bash $SAVE_DIR/mariadb_repo_setup --mariadb-server-version="mariadb-${MARIADB_TARGET_SERIES}" --skip-tools --skip-maxscale

    sudo apt-get update
    # devstack's own configure_database_mysql already edited /etc/mysql/mariadb.cnf
    # (bind-address, etc.), so dpkg sees a locally-modified conffile vs. the new
    # package's version here and would otherwise prompt interactively. Keep the
    # locally-modified version (same as the prompt's own default action) and
    # force a non-interactive frontend so it can't hang/fail waiting on stdin.
    #
    # mariadb-client-compat provides the `mysql`/`mysqldump`/etc. symlinks:
    # unlike the distro's mariadb-client, mariadb.org's package doesn't
    # install them by default, but grenade's own inc/upgrade:save_mysql_dbs
    # (and potentially other devstack/grenade code) still invokes `mysql`
    # directly, so this is needed for more than just our own scripts.
    sudo DEBIAN_FRONTEND=noninteractive apt-get install -y \
        -o Dpkg::Options::="--force-confold" \
        mariadb-server mariadb-client mariadb-client-compat

    sudo mariadb-upgrade

    restart_service $MYSQL_SERVICE_NAME

    # mariadb.org's own mariadb-client package no longer ships the `mysql`
    # compat symlink (unlike the distro's mariadb-server-provided client we
    # started on), so the CLI binary is `mariadb` from here on.
    local db_version
    db_version=$(sudo mariadb -e "select version();" -sN | cut -d '-' -f 1)
    if [[ "$db_version" != ${MARIADB_TARGET_SERIES}* ]]; then
        die $LINENO "MariaDB engine upgrade failed: expected version ${MARIADB_TARGET_SERIES}.x, got '$db_version'"
    fi
    echo "MariaDB engine upgraded successfully to $db_version"
}
