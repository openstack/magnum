
step="enable-occm-plugin"
printf "Starting to run ${step}\n"

. /etc/sysconfig/heat-params

occm_enabled=$(echo $CLOUD_PROVIDER_ENABLED | tr '[:upper:]' '[:lower:]')
ssh_cmd="ssh -F /srv/magnum/.ssh/config root@localhost"

if [[ "${occm_enabled}" = "true" ]]; then

_k8s_prefix=${CONTAINER_INFRA_PREFIX:-registry.k8s.io/provider-os/openstack-cloud-controller-manager}

OCCM_VALUES_YAML=/srv/magnum/kubernetes/helm/openstack-cloud-controller-manager/values.yaml
echo "Writing File: $OCCM_VALUES_YAML"
mkdir -p $(dirname ${OCCM_VALUES_YAML})
cat << EOF > ${OCCM_VALUES_YAML}
# Image repository name and tag
image:
  repository: ${_k8s_prefix}
  tag: "v1.24.6"

# Create a secret resource cloud-config (or other name) to store credentials and settings from cloudConfig
# You can also provide your own secret (not created by the Helm chart), in this case set create to false
# and adjust the name of the secret as necessary
secret:
  create: true
  name: cloud-config-occm

# Specify settings with the same key as the CCM config: https://github.com/kubernetes/cloud-provider-openstack/blob/master/docs/openstack-cloud-controller-manager/using-openstack-cloud-controller-manager.md#config-openstack-cloud-controller-manager
cloudConfig:
  global:
    auth-url: ${AUTH_URL}
    user-id: ${TRUSTEE_USER_ID}
    password: ${TRUSTEE_PASSWORD}
    trust-id: ${TRUST_ID}
    region: ${REGION_NAME}
    ca-file: /etc/kubernetes/ca-bundle.crt

# List of controllers should be enabled.
# Use '*' to enable all controllers.
# Prefix a controller with '-' to disable it.
enabledControllers:
  - cloud-node
  - cloud-node-lifecycle
  - service

nodeSelector:
  node-role.kubernetes.io/${LEAD_NODE_ROLE_NAME}: ""

# Set tolerations for nodes where the controller should run, i.e. node should uninitialized, controlplane...
tolerations:
  - key: node.cloudprovider.kubernetes.io/uninitialized
    value: "true"
    effect: NoSchedule
  - effect: NoSchedule
    operator: Exists
  - key: CriticalAddonsOnly
    operator: Exists
  - effect: NoExecute
    operator: Exists

# The following three volumes are required to use all OCCM controllers,
# but might not be needed if you just use a specific controller
# Additional volumes that should be available to the pods:
extraVolumes:
  - name: flexvolume-dir
    hostPath:
      path: /var/lib/kubelet/volumeplugins
  - name: k8s-certs
    hostPath:
      path: /etc/kubernetes
# Where the additional volumes should be mounted into the pods:
extraVolumeMounts:
  - name: flexvolume-dir
    mountPath: /var/lib/kubelet/volumeplugins
    readOnly: true
  - name: k8s-certs
    mountPath: /etc/kubernetes
    readOnly: true
controllerExtraArgs: |-
  - --use-service-account-credentials=false
cluster:
  name: ${CLUSTER_UUID}
EOF

$ssh_cmd helm repo add cpo https://kubernetes.github.io/cloud-provider-openstack

if $ssh_cmd helm plugin list | grep -q "mapkubeapis"; then
    echo "mapkubeapis is already installed."
else
    echo "mapkubeapis is not installed. Installing now..."
    $ssh_cmd helm plugin install https://github.com/helm/helm-mapkubeapis
fi
if $ssh_cmd helm list --namespace kube-system | grep -q "openstack-ccm"; then
    $ssh_cmd helm mapkubeapis openstack-ccm --namespace kube-system
fi
$ssh_cmd helm repo update
$ssh_cmd helm upgrade -i openstack-ccm cpo/openstack-cloud-controller-manager --version 2.27.1 -n kube-system -f ${OCCM_VALUES_YAML}

if $ssh_cmd helm list --namespace kube-system | grep -q "openstack-ccm"; then
    $ssh_cmd helm mapkubeapis openstack-ccm --namespace kube-system
fi

fi
printf "Finished running ${step}\n"