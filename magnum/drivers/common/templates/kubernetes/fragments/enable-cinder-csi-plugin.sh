#!/bin/sh

step="enable-cinder-csi-plugin"
printf "Starting to run ${step}\n"

. /etc/sysconfig/heat-params

volume_driver=$(echo "${VOLUME_DRIVER}" | tr '[:upper:]' '[:lower:]')
cinder_csi_plugin_enabled=$(echo $CINDER_CSI_PLUGIN_ENABLED | tr '[:upper:]' '[:lower:]')
ssh_cmd="ssh -F /srv/magnum/.ssh/config root@localhost"

if [ "${volume_driver}" = "cinder" ] && [ "${cinder_csi_plugin_enabled}" = "true" ]; then
    _cindercsi_prefix=${CONTAINER_INFRA_PREFIX:-registry.k8s.io/sig-storage/}
    _cinderplugin_prefix=${CONTAINER_INFRA_PREFIX:-registry.k8s.io/provider-os/}

CINDER_CSI_VALUES_YAML=/srv/magnum/kubernetes/helm/cinder-csi/values.yaml
    echo "Writing File: $CINDER_CSI_VALUES_YAML"
    mkdir -p $(dirname ${CINDER_CSI_VALUES_YAML})
    cat << EOF > ${CINDER_CSI_VALUES_YAML}
csi:
  attacher:
    image:
      repository: ${_cindercsi_prefix}csi-attacher
  provisioner:
    topology: "true"
    image:
      repository: ${_cindercsi_prefix}csi-provisioner
  snapshotter:
    image:
      repository: ${_cindercsi_prefix}csi-snapshotter
  resizer:
    image:
      repository: ${_cindercsi_prefix}csi-resizer
  livenessprobe:
    image:
      repository: ${_cindercsi_prefix}livenessprobe
  nodeDriverRegistrar:
    image:
      repository: ${_cindercsi_prefix}csi-node-driver-registrar
  plugin:
    image:
      repository: ${_cinderplugin_prefix}cinder-csi-plugin
    volumes:
      - name: cacert
        hostPath:
          path: /etc/kubernetes/ca-bundle.crt
          type: File
    volumeMounts:
      - name: cacert
        mountPath: /etc/kubernetes/certs/ca-bundle.crt
        readOnly: true
      - name: cloud-config
        mountPath: /etc/kubernetes/config/
        readOnly: true
    controllerPlugin:
      nodeSelector:
        node-role.kubernetes.io/${LEAD_NODE_ROLE_NAME}: ""
      tolerations:
      - effect: NoSchedule
        operator: Exists
      - key: CriticalAddonsOnly
        operator: Exists
      - effect: NoExecute
        operator: Exists
    nodePlugin:
      affinity: {}
      nodeSelector: {}
      tolerations:
        - operator: Exists
      kubeletDir: /var/lib/kubelet
  snapshotController:
    enabled: true
    image:
      repository: ${_cindercsi_prefix}snapshot-controller

secret:
  enabled: true
  create: true
  filename: config/cloud.conf
  name: cinder-csi-cloud-config
  data:
    cloud.conf: |-
      [Global]
      auth-url=${AUTH_URL}
      user-id=${TRUSTEE_USER_ID}
      password=${TRUSTEE_PASSWORD}
      trust-id=${TRUST_ID}
      region=${REGION_NAME}
      ca-file=/etc/kubernetes/certs/ca-bundle.crt

storageClass:
  enabled: true
  delete:
    isDefault: true
    allowVolumeExpansion: true
  retain:
    isDefault: false
    allowVolumeExpansion: true

# You may set ID of the cluster where openstack-cinder-csi is deployed. This value will be appended
# to volume metadata in newly provisioned volumes as cinder.csi.openstack.org/cluster=cluster ID.
clusterID: ${CLUSTER_UUID}

priorityClassName: ""
EOF


    echo "Waiting for Kubernetes API..."
    until  [ "ok" = "$(kubectl get --raw='/healthz' 2>nil)" ]
    do
        sleep 5
    done

    $ssh_cmd kubectl apply -f https://raw.githubusercontent.com/kubernetes-csi/external-snapshotter/release-6.2/client/config/crd/snapshot.storage.k8s.io_volumesnapshotclasses.yaml
    $ssh_cmd kubectl apply -f https://raw.githubusercontent.com/kubernetes-csi/external-snapshotter/release-6.2/client/config/crd/snapshot.storage.k8s.io_volumesnapshotcontents.yaml
    $ssh_cmd kubectl apply -f https://raw.githubusercontent.com/kubernetes-csi/external-snapshotter/release-6.2/client/config/crd/snapshot.storage.k8s.io_volumesnapshots.yaml

    $ssh_cmd helm repo add cpo https://kubernetes.github.io/cloud-provider-openstack

    if $ssh_cmd helm plugin list | grep -q "mapkubeapis"; then
        echo "mapkubeapis is already installed."
    else
        echo "mapkubeapis is not installed. Installing now..."
        $ssh_cmd helm plugin install https://github.com/helm/helm-mapkubeapis
    fi
    if $ssh_cmd helm list --namespace kube-system | grep -q "cinder-csi"; then
        $ssh_cmd helm mapkubeapis cinder-csi --namespace kube-system
    fi
    $ssh_cmd helm repo update
    $ssh_cmd helm upgrade -i cinder-csi cpo/openstack-cinder-csi --version 2.27.1 -n kube-system -f ${CINDER_CSI_VALUES_YAML}

    if $ssh_cmd helm list --namespace kube-system | grep -q "cinder-csi"; then
        $ssh_cmd helm mapkubeapis cinder-csi --namespace kube-system
    fi

    CINDER_CSI_VALUES_YAML_PATCH=/srv/magnum/kubernetes/helm/cinder-csi/patch.yaml
    echo "Writing File: $CINDER_CSI_VALUES_YAML_PATCH"
    mkdir -p $(dirname ${CINDER_CSI_VALUES_YAML_PATCH})
    cat << EOF > ${CINDER_CSI_VALUES_YAML_PATCH}
spec:
  template:
    spec:
      dnsPolicy: Default
EOF

    # Patch the deployment to use the default DNS policy
    $ssh_cmd kubectl patch deployment openstack-cinder-csi-controllerplugin --patch-file ${CINDER_CSI_VALUES_YAML_PATCH} -n kube-system

fi
printf "Finished running ${step}\n"
