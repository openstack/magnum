#!/bin/bash

. /etc/sysconfig/heat-params
set -x

ssh_cmd="ssh -F /srv/magnum/.ssh/config root@localhost"
KUBECONFIG="/etc/kubernetes/kubelet-config.yaml"
new_kube_tag="$kube_tag_input"

if [ ${new_kube_tag}!=${KUBE_TAG} ]; then
    # If there is only one master and this is the master node, skip the drain, just cordon it
    # If there is only one worker and this is the worker node, skip the drain, just cordon it
    all_masters=$(kubectl get nodes --selector=node-role.kubernetes.io/master= -o name)
    all_workers=$(kubectl get nodes --selector=node-role.kubernetes.io/master!= -o name)
    if [ "node/${INSTANCE_NAME}" != "${all_masters}" ] && [ "node/${INSTANCE_NAME}" != "${all_workers}" ]; then
        kubectl drain ${INSTANCE_NAME} --ignore-daemonsets --delete-local-data --force
    else
        kubectl cordon ${INSTANCE_NAME}
    fi

    SERVICE_LIST=$($ssh_cmd podman ps -f name=kube --format {{.Names}})

    for service in ${SERVICE_LIST}; do
        ${ssh_cmd} systemctl stop ${service}
        ${ssh_cmd} podman rm ${service}
    done

    ${ssh_cmd} podman rmi ${CONTAINER_INFRA_PREFIX:-k8s.gcr.io/}hyperkube:${KUBE_TAG}
    echo "KUBE_TAG=$new_kube_tag" >> /etc/sysconfig/heat-params

    for service in ${SERVICE_LIST}; do
        ${ssh_cmd} systemctl start ${service}
    done

    i=0
    until kubectl uncordon ${INSTANCE_NAME}
    do
        ((i++))
        [ $i -lt 30 ] || break;
        echo "Trying to uncordon node..."
        sleep 5s
    done
fi
