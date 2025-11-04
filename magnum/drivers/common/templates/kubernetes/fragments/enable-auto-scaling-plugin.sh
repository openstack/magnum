#!/bin/sh

step="enable-auto-scaling-plugin"
printf "Starting to run ${step}\n"

. /etc/sysconfig/heat-params

auto_scaling_plugin_enabled=$(echo $AUTO_SCALING_ENABLED | tr '[:upper:]' '[:lower:]')
ssh_cmd="ssh -F /srv/magnum/.ssh/config root@localhost"

if [[ "${auto_scaling_plugin_enabled}" = "true" || ("${auto_healing_enabled}" = "true" && "${autohealing_controller}" = "draino") ]]; then

_autoscaler_prefix=${CONTAINER_INFRA_PREFIX:-registry.k8s.io/autoscaling/}

CLUSTER_AUTOSCALER_VALUES_YAML=/srv/magnum/kubernetes/helm/cluster-autoscaler/values.yaml
    echo "Writing File: $CLUSTER_AUTOSCALER_VALUES_YAML"
    mkdir -p $(dirname ${CLUSTER_AUTOSCALER_VALUES_YAML})
    cat << EOF > ${CLUSTER_AUTOSCALER_VALUES_YAML}
magnumClusterName: ${CLUSTER_UUID}
image:
  repository: ${_autoscaler_prefix}cluster-autoscaler
cloudProvider: magnum
nameOverride: manager
cloudConfigPath: /etc/kubernetes/cloud-config
autoDiscovery:
  clusterName: ${CLUSTER_UUID}
  roles:
    - worker
# autoscalingGroups:
#  - name: default-worker
#    minSize: ${MIN_NODE_COUNT}
#    maxSize: ${MAX_NODE_COUNT}
extraArgs:
  logtostderr: true
  stderrthreshold: info
  v: 4
  leader-elect-lease-duration: 40s
  leader-elect-renew-deadline: 20s
nodeSelector:
  node-role.kubernetes.io/${LEAD_NODE_ROLE_NAME}: ""
tolerations: 
  - effect: NoSchedule
    operator: Exists
  - key: CriticalAddonsOnly
    operator: Exists
  - effect: NoExecute
    operator: Exists
dnsPolicy: Default
priorityClassName: "system-cluster-critical"

EOF



$ssh_cmd helm repo add autoscaler https://kubernetes.github.io/autoscaler

if $ssh_cmd helm plugin list | grep -q "mapkubeapis"; then
    echo "mapkubeapis is already installed."
else
    echo "mapkubeapis is not installed. Installing now..."
    $ssh_cmd helm plugin install https://github.com/helm/helm-mapkubeapis
fi
if $ssh_cmd helm list --namespace kube-system | grep -q "openstack-autoscaler"; then
    $ssh_cmd helm mapkubeapis openstack-autoscaler --namespace kube-system
fi
$ssh_cmd helm repo update
$ssh_cmd helm upgrade -i openstack-autoscaler autoscaler/cluster-autoscaler --version 9.29.1 -n kube-system -f ${CLUSTER_AUTOSCALER_VALUES_YAML}

if $ssh_cmd helm list --namespace kube-system | grep -q "openstack-autoscaler"; then
    $ssh_cmd helm mapkubeapis openstack-autoscaler --namespace kube-system
fi

fi
printf "Finished running ${step}\n"
