#!/bin/sh

step="deprecation"
printf "Starting to run ${step}\n"

. /etc/sysconfig/heat-params

ssh_cmd="ssh -F /srv/magnum/.ssh/config root@localhost"

is_upgrade=$(echo $IS_UPGRADE | tr '[:upper:]' '[:lower:]')

if [ "${is_upgrade}" = "true" ]; then
    echo "Waiting for Kubernetes API..."
    until  [ "ok" = "$(kubectl get --raw='/healthz' 2>nil)" ]
    do
        sleep 5
    done

    # Delete old npd as it migrated to helm
    NPD_DEPLOY=/srv/magnum/kubernetes/manifests/npd.yaml
    $ssh_cmd kubectl delete -f "${NPD_DEPLOY}" --ignore-not-found=true

    # Delete old draino as it deprecated
    DRAINO_DEPLOY=/srv/magnum/kubernetes/manifests/draino.yaml
    $ssh_cmd kubectl delete -f "${DRAINO_DEPLOY}" --ignore-not-found=true

    # Delete k8s-keystone-auth
    K8AUTH_DEPLOY=/srv/magnum/kubernetes/manifests/k8s-keystone-auth.yaml
    $ssh_cmd kubectl delete -f "${K8AUTH_DEPLOY}" --ignore-not-found=true
    K8AUTHP_DEPLOY=/srv/magnum/kubernetes/keystone-auth-policy.yaml
    $ssh_cmd kubectl delete -f "${K8AUTHP_DEPLOY}" --ignore-not-found=true

    DASHBOARD_DEPLOY=/srv/magnum/kubernetes/kubernetes-dashboard.yaml
    $ssh_cmd kubectl delete -f "${DASHBOARD_DEPLOY}" --ignore-not-found=true

    # Delete old occ as it migrated to helm
    OCC_DEPLOY=/srv/magnum/kubernetes/openstack-cloud-controller-manager.yaml
    $ssh_cmd kubectl delete -f "${OCC_DEPLOY}" --ignore-not-found=true

    # Delete old magnum release as it deprecated
    $ssh_cmd helm uninstall magnum -n kube-system 2>/dev/nul

    ## delete old flannel before upgrade
    $ssh_cmd kubectl delete ds kube-flannel-ds -n kube-system --ignore-not-found=true
    $ssh_cmd kubectl delete ConfigMap kube-flannel-cfg -n kube-system --ignore-not-found=true
    $ssh_cmd kubectl delete ServiceAccount flannel -n kube-system --ignore-not-found=true
    $ssh_cmd kubectl delete ClusterRoleBinding flannel -n kube-system --ignore-not-found=true
    $ssh_cmd kubectl delete ClusterRole flannel -n kube-system --ignore-not-found=true
fi
printf "Finished running ${step}\n"
