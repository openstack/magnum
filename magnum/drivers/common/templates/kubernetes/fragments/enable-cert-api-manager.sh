#!/bin/sh

step="enable-cert-api-manager"
printf "Starting to run ${step}\n"

. /etc/sysconfig/heat-params

if [ "$(echo "${CERT_MANAGER_API}" | tr '[:upper:]' '[:lower:]')" = "true" ]; then
    cert_dir=/etc/kubernetes/certs

    # Only write CA key if it doesn't exist
    if [ ! -f "${cert_dir}/ca.key" ]; then
        echo -e "${CA_KEY}" > ${cert_dir}/ca.key
        chmod 400 ${cert_dir}/ca.key
    fi
fi

printf "Finished running ${step}\n"
