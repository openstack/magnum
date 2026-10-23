#!/usr/bin/env bash

# ``upgrade-magnum``

echo "*********************************************************************"
echo "Begin $0"
echo "*********************************************************************"

cleanup() {
    set +o errexit

    echo "*********************************************************************"
    echo "ERROR: Abort $0"
    echo "*********************************************************************"

    trap 2; kill -2 $$
}
trap cleanup SIGHUP SIGINT SIGTERM

RUN_DIR=$(cd $(dirname "$0") && pwd)

source $GRENADE_DIR/grenaderc
source $GRENADE_DIR/functions

set -o errexit

source $TARGET_DEVSTACK_DIR/stackrc
source $TARGET_RELEASE_DIR/magnum/devstack/lib/magnum
source $RUN_DIR/mariadb_upgrade.sh

set -o xtrace

# MariaDB engine bump must happen first: magnum-db-manage upgrade below needs
# a DB already on its final version. Accepted trade-off: by this point other
# already-upgraded projects (keystone, nova, cinder, barbican, octavia, ...)
# are live against this same instance and will see a brief connection blip
# when it restarts -- not something grenade's project ordering lets us avoid
# cleanly, so it's accepted rather than engineered around.
upgrade_mariadb_engine

[[ -d $SAVE_DIR/etc.magnum ]] || cp -pr $MAGNUM_CONF_DIR $SAVE_DIR/etc.magnum

# install_magnum()
stack_install_service magnum

# Reinstall magnum-cluster-api from the target checkout when present
if [[ -d $DEST/magnum-cluster-api ]]; then
    setup_develop $DEST/magnum-cluster-api
fi

if [[ -d $DEST/magnum-capi-helm ]]; then
    setup_develop $DEST/magnum-capi-helm
fi

# Migrate the database
$MAGNUM_BIN_DIR/magnum-db-manage upgrade

# Start magnum
start_magnum
ensure_services_started magnum-api magnum-cond

set +o xtrace
echo "*********************************************************************"
echo "SUCCESS: End $0"
echo "*********************************************************************"
