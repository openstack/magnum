#!/bin/sh

set -eux

MAGNUM_DIR=$(readlink -f $(dirname $0)/../..)
INSTALL_DIR=${INSTALL_DIR:-/opt/stack}

cp ${MAGNUM_DIR}/contrib/devstack/lib/magnum ${INSTALL_DIR}/devstack/lib
cp ${MAGNUM_DIR}/contrib/devstack/extras.d/70-magnum.sh ${INSTALL_DIR}/devstack/extras.d

# Add magnum specific requirements to global requirements
git clone https://git.openstack.org/openstack/requirements ${INSTALL_DIR}/requirements || true
echo "python-kubernetes>=0.2" >> ${INSTALL_DIR}/requirements/global-requirements.txt
echo "docker-py>=0.5.1" >> ${INSTALL_DIR}/requirements/global-requirements.txt
