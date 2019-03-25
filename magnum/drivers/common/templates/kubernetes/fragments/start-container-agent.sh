#!/bin/bash

. /etc/sysconfig/heat-params

set -ux

if [ ! -z "$HTTP_PROXY" ]; then
    export HTTP_PROXY
fi

if [ ! -z "$HTTPS_PROXY" ]; then
    export HTTPS_PROXY
fi

if [ ! -z "$NO_PROXY" ]; then
    export NO_PROXY
fi

_prefix=${CONTAINER_INFRA_PREFIX:-docker.io/openstackmagnum/}
atomic install \
--storage ostree \
--system \
--system-package no \
--set REQUESTS_CA_BUNDLE=/etc/pki/tls/certs/ca-bundle.crt \
--name heat-container-agent \
${_prefix}heat-container-agent:${HEAT_CONTAINER_AGENT_TAG}

systemctl start heat-container-agent
