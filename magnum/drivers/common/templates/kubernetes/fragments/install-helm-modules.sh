#!/bin/bash

step="install-helm-modules.sh"
printf "Starting to run ${step}\n"

. /etc/sysconfig/heat-params

set -ex

echo "Waiting for Kubernetes API..."
until  [ "ok" = "$(curl --silent http://127.0.0.1:8080/healthz)" ]
do
    sleep 5
done

if [ "$(echo ${TILLER_ENABLED} | tr '[:upper:]' '[:lower:]')" != "true" ]; then
    echo "Use --labels tiller_enabled=True to allow for tiller dependent resources to be installed"
else
    HELM_MODULES_PATH="/srv/magnum/kubernetes/helm"
    mkdir -p ${HELM_MODULES_PATH}
    helm_modules=(${HELM_MODULES_PATH}/*)

    # Only run kubectl if we have modules to install
    if [ "${helm_modules}" != "${HELM_MODULES_PATH}/*" ]; then
        for module in "${helm_modules[@]}"; do
            echo "Applying ${module}."
            kubectl apply -f ${module}
        done
    fi
fi

printf "Finished running ${step}\n"
