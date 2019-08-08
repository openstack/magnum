#!/bin/bash

. /etc/sysconfig/heat-params
set -x

ssh_cmd="ssh -F /srv/magnum/.ssh/config root@localhost"
kubecontrol="/var/lib/containers/atomic/heat-container-agent.0/rootfs/usr/bin/kubectl --kubeconfig /etc/kubernetes/kubelet-config.yaml"
new_kube_tag="$kube_tag_input"

if [ ${new_kube_tag}!=${KUBE_TAG} ]; then
    # If there is only one master and this is the master node, skip the drain, just cordon it
    # If there is only one worker and this is the worker node, skip the drain, just cordon it
    all_masters=$(${ssh_cmd} ${kubecontrol} get nodes --selector=node-role.kubernetes.io/master= -o name)
    all_workers=$(${ssh_cmd} ${kubecontrol} get nodes --selector=node-role.kubernetes.io/master!= -o name)
    if [ "node/${INSTANCE_NAME}" != "${all_masters}" ] && [ "node/${INSTANCE_NAME}" != "${all_workers}" ]; then
        ${ssh_cmd} ${kubecontrol} drain ${INSTANCE_NAME} --ignore-daemonsets --delete-local-data --force
    else
        ${ssh_cmd} ${kubecontrol} cordon ${INSTANCE_NAME}
    fi

    declare -A service_image_mapping
    service_image_mapping=( ["kubelet"]="kubernetes-kubelet" ["kube-controller-manager"]="kubernetes-controller-manager" ["kube-scheduler"]="kubernetes-scheduler" ["kube-proxy"]="kubernetes-proxy" ["kube-apiserver"]="kubernetes-apiserver" )

    SERVICE_LIST=$($ssh_cmd atomic containers list -f container=kube -q --no-trunc)

    for service in ${SERVICE_LIST}; do
        ${ssh_cmd} systemctl stop ${service}
    done

    for service in ${SERVICE_LIST}; do
        ${ssh_cmd} atomic pull --storage ostree "docker.io/openstackmagnum/${service_image_mapping[${service}]}:${new_kube_tag}"
    done

    for service in ${SERVICE_LIST}; do
        ${ssh_cmd} atomic containers update --rebase docker.io/openstackmagnum/${service_image_mapping[${service}]}:${new_kube_tag} ${service}
    done

    for service in ${SERVICE_LIST}; do
        systemctl restart ${service}
    done

    ${ssh_cmd} /var/lib/containers/atomic/heat-container-agent.0/rootfs/usr/bin/kubectl --kubeconfig /etc/kubernetes/kubelet-config.yaml uncordon ${INSTANCE_NAME}

    for service in ${SERVICE_LIST}; do
        ${ssh_cmd} atomic --assumeyes images "delete docker.io/openstackmagnum/${service_image_mapping[${service}]}:${KUBE_TAG}"
    done

    ${ssh_cmd} atomic images prune

    # Appending the new KUBE_TAG into the heat-parms to log and indicate the current k8s version
    echo "KUBE_TAG=$new_kube_tag" >> /etc/sysconfig/heat-params
fi
