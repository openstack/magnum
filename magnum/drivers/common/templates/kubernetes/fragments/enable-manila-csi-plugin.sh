#!/bin/sh

step="enable-manila-csi-plugin"
printf "Starting to run ${step}\n"

. /etc/sysconfig/heat-params

manila_csi_plugin_enabled=$(echo $MANILA_CSI_PLUGIN_ENABLED | tr '[:upper:]' '[:lower:]')
ssh_cmd="ssh -F /srv/magnum/.ssh/config root@localhost"

if [ "${manila_csi_plugin_enabled}" = "true" ]; then
    csi_driver_path="/srv/magnum/kubernetes/csi-driver-nfs"
    csi_driver_branch="master"
    rm -rf ${csi_driver_path}
    mkdir -p ${csi_driver_path}
    curl -L https://github.com/kubernetes-csi/csi-driver-nfs/archive/${csi_driver_branch}.tar.gz -o ${csi_driver_path}/${csi_driver_branch}.tar.gz
    tar -xzf ${csi_driver_path}/${csi_driver_branch}.tar.gz -C ${csi_driver_path}
    $ssh_cmd helm package ${csi_driver_path}/csi-driver-nfs-${csi_driver_branch}/charts/v2.0.0/csi-driver-nfs -d ${csi_driver_path}/package
    $ssh_cmd helm upgrade -i nfs-driver $(ls -d ${csi_driver_path}/package/*) -n kube-system \
         --set controller.replicas=2

    csi_plugin_path="/srv/magnum/kubernetes/manila-csi-plugin"
    csi_plugin_branch="release-1.20"
    rm -rf ${csi_plugin_path}
    mkdir -p ${csi_plugin_path}
    curl -L https://github.com/kubernetes/cloud-provider-openstack/archive/${csi_plugin_branch}.tar.gz -o ${csi_plugin_path}/${csi_plugin_branch}.tar.gz
    tar -xzf ${csi_plugin_path}/${csi_plugin_branch}.tar.gz -C ${csi_plugin_path}
    $ssh_cmd helm package ${csi_plugin_path}/cloud-provider-openstack-${csi_plugin_branch}/charts/manila-csi-plugin -d ${csi_plugin_path}/package
    $ssh_cmd helm upgrade -i openstack-manila-csi $(ls -d ${csi_plugin_path}/package/*) -n kube-system \
         --set fullnameOverride="" \
         --set shareProtocols[0].protocolSelector=NFS \
         --set shareProtocols[0].fwdNodePluginEndpoint.dir=/var/lib/kubelet/plugins/csi-nfsplugin \
         --set shareProtocols[0].fwdNodePluginEndpoint.sockFile=csi.sock


cat <<EOF | kubectl apply -f -
---
apiVersion: v1
kind: Secret
metadata:
  name: csi-manila-secrets
  namespace: kube-system
type: Opaque
stringData:
  os-authURL: "$AUTH_URL"
  os-region: "$REGION_NAME"
  os-trustID: "$TRUST_ID"
  os-trusteeID: "$TRUSTEE_USER_ID"
  os-trusteePassword: "$TRUSTEE_PASSWORD"
EOF


cat <<EOF | kubectl apply -f -
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: csi-manila-nfs
provisioner: nfs.manila.csi.openstack.org
parameters:
  type: cephfsnfs1

  csi.storage.k8s.io/provisioner-secret-name: csi-manila-secrets
  csi.storage.k8s.io/provisioner-secret-namespace: kube-system
  csi.storage.k8s.io/node-stage-secret-name: csi-manila-secrets
  csi.storage.k8s.io/node-stage-secret-namespace: kube-system
  csi.storage.k8s.io/node-publish-secret-name: csi-manila-secrets
  csi.storage.k8s.io/node-publish-secret-namespace: kube-system
EOF

fi
printf "Finished running ${step}\n"
