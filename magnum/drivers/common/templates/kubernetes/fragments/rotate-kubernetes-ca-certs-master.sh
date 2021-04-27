echo "START: rotate CA certs on master"

set +x
. /etc/sysconfig/heat-params
set -x

set -eu -o pipefail

ssh_cmd="ssh -F /srv/magnum/.ssh/config root@localhost"
export KUBECONFIG="/etc/kubernetes/admin.conf"

service_account_key=$kube_service_account_key_input
service_account_private_key=$kube_service_account_private_key_input

if [ ! -z "$service_account_key" ] && [ ! -z "$service_account_private_key" ] ; then

    # Follow the instructions on  https://kubernetes.io/docs/tasks/tls/manual-rotation-of-ca-certificates/
    for namespace in $(kubectl get namespace -o jsonpath='{.items[*].metadata.name}'); do
        for name in $(kubectl get deployments -n $namespace -o jsonpath='{.items[*].metadata.name}'); do
            kubectl patch deployment -n ${namespace} ${name} -p '{"spec":{"template":{"metadata":{"annotations":{"ca-rotation": "1"}}}}}';
        done
        for name in $(kubectl get daemonset -n $namespace -o jsonpath='{.items[*].metadata.name}'); do
            kubectl patch daemonset -n ${namespace} ${name} -p '{"spec":{"template":{"metadata":{"annotations":{"ca-rotation": "1"}}}}}';
        done
    done

    # Annotate any Daemonsets and Deployments to trigger pod replacement in a safer rolling fashion.
    for namespace in $(kubectl get namespace -o jsonpath='{.items[*].metadata.name}'); do
        for name in $(kubectl get deployments -n $namespace -o jsonpath='{.items[*].metadata.name}'); do
            kubectl patch deployment -n ${namespace} ${name} -p '{"spec":{"template":{"metadata":{"annotations":{"ca-rotation": "1"}}}}}';
        done
        for name in $(kubectl get daemonset -n $namespace -o jsonpath='{.items[*].metadata.name}'); do
            kubectl patch daemonset -n ${namespace} ${name} -p '{"spec":{"template":{"metadata":{"annotations":{"ca-rotation": "1"}}}}}';
        done
    done

    for service in etcd kube-apiserver kube-controller-manager kube-scheduler kubelet kube-proxy; do
        echo "restart service $service"
        $ssh_cmd systemctl restart $service
    done

    # NOTE(flwang): Re-patch the calico-node daemonset again to make sure all pods are being recreated
    kubectl patch daemonset -n kube-system calico-node -p '{"spec":{"template":{"metadata":{"annotations":{"ca-rotation": "2"}}}}}';
fi

echo "END: rotate CA certs on master"
