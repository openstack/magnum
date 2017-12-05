#!/bin/sh

CACERTS=$(cat <<-EOF
@@CACERTS_CONTENT@@
EOF
)

CA_FILE=/usr/local/share/ca-certificates/magnum-external.crt

if [ -n "$CACERTS" ]; then
    touch $CA_FILE
    echo "$CACERTS" | tee -a $CA_FILE
    chmod 0644 $CA_FILE
    chown root:root $CA_FILE
    update-ca-certificates
    # Legacy versions of requests shipped with os-collect-config can have own CA cert database
    for REQUESTS_LOCATION in \
        /opt/stack/venvs/os-collect-config/lib/python2.7/site-packages/requests \
        /usr/local/lib/python2.7/dist-packages/requests; do
        if [ -f "${REQUESTS_LOCATION}/cacert.pem" ]; then
            echo "$CACERTS" | tee -a "${REQUESTS_LOCATION}/cacert.pem"
        fi
    done
    if [ -f /etc/init/os-collect-config.conf ]; then
        service os-collect-config restart
    fi
fi
