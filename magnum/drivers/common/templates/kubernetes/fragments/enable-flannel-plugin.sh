#!/bin/sh

step="enable-flannel-plugin"
printf "Starting to run ${step}\n"

. /etc/sysconfig/heat-params

ssh_cmd="ssh -F /srv/magnum/.ssh/config root@localhost"

if [ "$NETWORK_DRIVER" = "flannel" ]; then
    _prefix=${CONTAINER_INFRA_PREFIX:-quay.io/coreos/}
    FLANNEL_NS=/srv/magnum/kubernetes/manifests/flannel-namespace.yaml

    echo "Writing File: $FLANNEL_NS"
    mkdir -p "$(dirname ${FLANNEL_NS})"
    set +x
    cat << EOF > ${FLANNEL_NS}
---
kind: Namespace
apiVersion: v1
metadata:
  name: kube-flannel
  labels:
    pod-security.kubernetes.io/enforce: privileged
EOF

FLANNEL_VALUES_YAML=/srv/magnum/kubernetes/helm/flannel/values.yaml
    echo "Writing File: $FLANNEL_VALUES_YAML"
    mkdir -p $(dirname ${FLANNEL_VALUES_YAML})
    cat << EOF > ${FLANNEL_VALUES_YAML}
---
# The IPv4 cidr pool to create on startup if none exists. Pod IPs will be
# chosen from this range.
podCidr: "${FLANNEL_NETWORK_CIDR}"

flannel:
  backend: "${FLANNEL_BACKEND}"
EOF

    set -x

    if [ "$MASTER_INDEX" = "0" ]; then

        until  [ "ok" = "$(kubectl get --raw='/healthz' 2>nil)" ]
        do
            echo "Waiting for Kubernetes API..."
            sleep 5
        done
    fi

    $ssh_cmd kubectl apply -f "${FLANNEL_NS}"

    $ssh_cmd helm repo add flannel https://flannel-io.github.io/flannel/

    if $ssh_cmd helm plugin list | grep -q "mapkubeapis"; then
        echo "mapkubeapis is already installed."
    else
        echo "mapkubeapis is not installed. Installing now..."
        $ssh_cmd helm plugin install https://github.com/helm/helm-mapkubeapis
    fi
    if $ssh_cmd helm list --namespace kube-flannel| grep -q "flannel"; then
        $ssh_cmd helm mapkubeapis flannel --namespace kube-flannel
    fi
    $ssh_cmd helm repo update
    $ssh_cmd helm upgrade -i flannel flannel/flannel --version ${FLANNEL_TAG} -n kube-flannel -f ${FLANNEL_VALUES_YAML}
    
    if $ssh_cmd helm list --namespace kube-flannel| grep -q "flannel"; then
        $ssh_cmd helm mapkubeapis flannel --namespace kube-flannel
    fi
fi


printf "Finished running ${step}\n"
