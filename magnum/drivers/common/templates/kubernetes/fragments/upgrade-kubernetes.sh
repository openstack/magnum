#!/bin/bash

. /etc/sysconfig/heat-params
set -x

ssh_cmd="ssh -F /srv/magnum/.ssh/config root@localhost"
kubecontrol="/var/lib/containers/atomic/heat-container-agent.0/rootfs/usr/bin/kubectl --kubeconfig /etc/kubernetes/kubelet-config.yaml"
new_kube_tag="$kube_tag_input"

if [ ${new_kube_tag}!=${KUBE_TAG} ]; then
    HOSTNAME_OVERRIDE="$(cat /etc/hostname | head -1 | sed 's/\.novalocal//')"
    # If there is only one master and this is the master node, skip the drain, just cordon it
    # If there is only one worker and this is the worker node, skip the drain, just cordon it
    all_masters=$(${ssh_cmd} ${kubecontrol} get nodes --selector=node-role.kubernetes.io/master= -o name)
    all_workers=$(${ssh_cmd} ${kubecontrol} get nodes --selector=node-role.kubernetes.io/master!= -o name)
    if [ "node/${HOSTNAME_OVERRIDE}" != "${all_masters}" ] && [ "node/${HOSTNAME_OVERRIDE}" != "${all_workers}" ]; then
        ${ssh_cmd} ${kubecontrol} drain ${HOSTNAME_OVERRIDE} --ignore-daemonsets --delete-local-data --force
    else
        ${ssh_cmd} ${kubecontrol} cordon ${HOSTNAME_OVERRIDE}
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

    ${ssh_cmd} /var/lib/containers/atomic/heat-container-agent.0/rootfs/usr/bin/kubectl --kubeconfig /etc/kubernetes/kubelet-config.yaml uncordon ${HOSTNAME_OVERRIDE}

    # FIXME(flwang): The KUBE_TAG could be out of date after a successful upgrade
    for service in ${SERVICE_LIST}; do
        ${ssh_cmd} atomic --assumeyes images "delete docker.io/openstackmagnum/${service_image_mapping[${service}]}:${KUBE_TAG}"
    done

    ${ssh_cmd} atomic images prune

fi
