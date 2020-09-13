echo "START: rotate CA certs on worker"

set +x
. /etc/sysconfig/heat-params
set -x

set -eu -o pipefail

ssh_cmd="ssh -F /srv/magnum/.ssh/config root@localhost"

service_account_key=$kube_service_account_key_input
service_account_private_key=$kube_service_account_private_key_input

if [ ! -z "$service_account_key" ] && [ ! -z "$service_account_private_key" ] ; then

    for service in kubelet kube-proxy; do
        echo "restart service $service"
        $ssh_cmd systemctl restart $service
    done
fi

echo "END: rotate CA certs on worker"
