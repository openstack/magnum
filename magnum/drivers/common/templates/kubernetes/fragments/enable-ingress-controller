#!/bin/bash

# Enables the specified ingress controller.
#
# Currently there is only support for traefik.
. /etc/sysconfig/heat-params

function writeFile {
    # $1 is filename
    # $2 is file content

    [ -f ${1} ] || {
        echo "Writing File: $1"
        mkdir -p $(dirname ${1})
        cat << EOF > ${1}
$2
EOF
    }
}

if [ "$(echo $INGRESS_CONTROLLER | tr '[:upper:]' '[:lower:]')" = "traefik" ]; then
    $enable-ingress-traefik
fi
