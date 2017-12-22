#!/bin/bash

. /etc/sysconfig/heat-params

if [ "$(echo $CERT_MANAGER_API | tr '[:upper:]' '[:lower:]')" = "false" ]; then
    exit 0
fi

cert_dir=/etc/kubernetes/certs

echo -e "$CA_KEY" > ${cert_dir}/ca.key

chown kube.kube ${cert_dir}/ca.key
chmod 400 ${cert_dir}/ca.key

