step="enable-cinder-csi"
printf "Starting to run ${step}\n"

. /etc/sysconfig/heat-params

volume_driver=$(echo "${VOLUME_DRIVER}" | tr '[:upper:]' '[:lower:]')
cinder_csi_enabled=$(echo $CINDER_CSI_ENABLED | tr '[:upper:]' '[:lower:]')

if [ "${volume_driver}" = "cinder" ] && [ "${cinder_csi_enabled}" = "true" ]; then
    # Generate Cinder CSI manifest file
    CINDER_CSI_DEPLOY=/srv/magnum/kubernetes/manifests/cinder-csi.yaml
    echo "Writing File: $CINDER_CSI_DEPLOY"
    mkdir -p $(dirname ${CINDER_CSI_DEPLOY})
    cat << EOF > ${CINDER_CSI_DEPLOY}
---
# This YAML file contains RBAC API objects,
# which are necessary to run csi controller plugin
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: csi-cinder-controller-sa
  namespace: kube-system
---
# external attacher
kind: ClusterRole
apiVersion: rbac.authorization.k8s.io/v1
metadata:
  name: csi-attacher-role
rules:
  - apiGroups: [""]
    resources: ["persistentvolumes"]
    verbs: ["get", "list", "watch", "update", "patch"]
  - apiGroups: [""]
    resources: ["nodes"]
    verbs: ["get", "list", "watch"]
  - apiGroups: ["storage.k8s.io"]
    resources: ["volumeattachments"]
    verbs: ["get", "list", "watch", "update", "patch"]
  - apiGroups: ["storage.k8s.io"]
    resources: ["csinodes"]
    verbs: ["get", "list", "watch"]
---
kind: ClusterRoleBinding
apiVersion: rbac.authorization.k8s.io/v1
metadata:
  name: csi-attacher-binding
subjects:
  - kind: ServiceAccount
    name: csi-cinder-controller-sa
    namespace: kube-system
roleRef:
  kind: ClusterRole
  name: csi-attacher-role
  apiGroup: rbac.authorization.k8s.io
---
# external Provisioner
kind: ClusterRole
apiVersion: rbac.authorization.k8s.io/v1
metadata:
  name: csi-provisioner-role
rules:
  - apiGroups: [""]
    resources: ["persistentvolumes"]
    verbs: ["get", "list", "watch", "create", "delete"]
  - apiGroups: [""]
    resources: ["persistentvolumeclaims"]
    verbs: ["get", "list", "watch", "update"]
  - apiGroups: ["storage.k8s.io"]
    resources: ["storageclasses"]
    verbs: ["get", "list", "watch"]
  - apiGroups: [""]
    resources: ["nodes"]
    verbs: ["get", "list", "watch"]
  - apiGroups: ["storage.k8s.io"]
    resources: ["csinodes"]
    verbs: ["get", "list", "watch"]
  - apiGroups: [""]
    resources: ["events"]
    verbs: ["list", "watch", "create", "update", "patch"]
  - apiGroups: ["snapshot.storage.k8s.io"]
    resources: ["volumesnapshots"]
    verbs: ["get", "list"]
  - apiGroups: ["snapshot.storage.k8s.io"]
    resources: ["volumesnapshotcontents"]
    verbs: ["get", "list"]
---
kind: ClusterRoleBinding
apiVersion: rbac.authorization.k8s.io/v1
metadata:
  name: csi-provisioner-binding
subjects:
  - kind: ServiceAccount
    name: csi-cinder-controller-sa
    namespace: kube-system
roleRef:
  kind: ClusterRole
  name: csi-provisioner-role
  apiGroup: rbac.authorization.k8s.io
---
# external snapshotter
kind: ClusterRole
apiVersion: rbac.authorization.k8s.io/v1
metadata:
  name: csi-snapshotter-role
rules:
  - apiGroups: [""]
    resources: ["persistentvolumes"]
    verbs: ["get", "list", "watch"]
  - apiGroups: [""]
    resources: ["persistentvolumeclaims"]
    verbs: ["get", "list", "watch"]
  - apiGroups: ["storage.k8s.io"]
    resources: ["storageclasses"]
    verbs: ["get", "list", "watch"]
  - apiGroups: [""]
    resources: ["events"]
    verbs: ["list", "watch", "create", "update", "patch"]
  - apiGroups: [""]
    resources: ["secrets"]
    verbs: ["get", "list"]
  - apiGroups: ["snapshot.storage.k8s.io"]
    resources: ["volumesnapshotclasses"]
    verbs: ["get", "list", "watch"]
  - apiGroups: ["snapshot.storage.k8s.io"]
    resources: ["volumesnapshotcontents"]
    verbs: ["create", "get", "list", "watch", "update", "delete"]
  - apiGroups: ["snapshot.storage.k8s.io"]
    resources: ["volumesnapshots"]
    verbs: ["get", "list", "watch", "update"]
  - apiGroups: ["snapshot.storage.k8s.io"]
    resources: ["volumesnapshots/status"]
    verbs: ["update"]
  - apiGroups: ["apiextensions.k8s.io"]
    resources: ["customresourcedefinitions"]
    verbs: ["create", "list", "watch", "delete"]
---
kind: ClusterRoleBinding
apiVersion: rbac.authorization.k8s.io/v1
metadata:
  name: csi-snapshotter-binding
subjects:
  - kind: ServiceAccount
    name: csi-cinder-controller-sa
    namespace: kube-system
roleRef:
  kind: ClusterRole
  name: csi-snapshotter-role
  apiGroup: rbac.authorization.k8s.io
---
# External Resizer
kind: ClusterRole
apiVersion: rbac.authorization.k8s.io/v1
metadata:
  name: csi-resizer-role
rules:
  # The following rule should be uncommented for plugins that require secrets
  # for provisioning.
  # - apiGroups: [""]
  #   resources: ["secrets"]
  #   verbs: ["get", "list", "watch"]
  - apiGroups: [""]
    resources: ["persistentvolumes"]
    verbs: ["get", "list", "watch", "update", "patch"]
  - apiGroups: [""]
    resources: ["persistentvolumeclaims"]
    verbs: ["get", "list", "watch"]
  - apiGroups: [""]
    resources: ["persistentvolumeclaims/status"]
    verbs: ["update", "patch"]
  - apiGroups: ["storage.k8s.io"]
    resources: ["storageclasses"]
    verbs: ["get", "list", "watch"]
  - apiGroups: [""]
    resources: ["events"]
    verbs: ["list", "watch", "create", "update", "patch"]
---
kind: ClusterRoleBinding
apiVersion: rbac.authorization.k8s.io/v1
metadata:
  name: csi-resizer-binding
subjects:
  - kind: ServiceAccount
    name: csi-cinder-controller-sa
    namespace: kube-system
roleRef:
  kind: ClusterRole
  name: csi-resizer-role
  apiGroup: rbac.authorization.k8s.io
---
kind: Role
apiVersion: rbac.authorization.k8s.io/v1
metadata:
  namespace: kube-system
  name: external-resizer-cfg
rules:
- apiGroups: ["coordination.k8s.io"]
  resources: ["leases"]
  verbs: ["get", "watch", "list", "delete", "update", "create"]
---
kind: RoleBinding
apiVersion: rbac.authorization.k8s.io/v1
metadata:
  name: csi-resizer-role-cfg
  namespace: kube-system
subjects:
  - kind: ServiceAccount
    name: csi-cinder-controller-sa
    namespace: kube-system
roleRef:
  kind: Role
  name: external-resizer-cfg
  apiGroup: rbac.authorization.k8s.io
---
# This YAML file contains CSI Controller Plugin Sidecars
# external-attacher, external-provisioner, external-snapshotter
---
kind: Service
apiVersion: v1
metadata:
  name: csi-cinder-controller-service
  namespace: kube-system
  labels:
    app: csi-cinder-controllerplugin
spec:
  selector:
    app: csi-cinder-controllerplugin
  ports:
    - name: dummy
      port: 12345
---
kind: StatefulSet
apiVersion: apps/v1
metadata:
  name: csi-cinder-controllerplugin
  namespace: kube-system
spec:
  serviceName: "csi-cinder-controller-service"
  replicas: 1
  selector:
    matchLabels:
      app: csi-cinder-controllerplugin
  template:
    metadata:
      labels:
        app: csi-cinder-controllerplugin
    spec:
      serviceAccount: csi-cinder-controller-sa
      tolerations:
        # Make sure the pod can be scheduled on master kubelet.
        - effect: NoSchedule
          operator: Exists
        # Mark the pod as a critical add-on for rescheduling.
        - key: CriticalAddonsOnly
          operator: Exists
      nodeSelector:
        node-role.kubernetes.io/master: ""
      containers:
        - name: csi-attacher
          image: ${CONTAINER_INFRA_PREFIX:-quay.io/k8scsi/}csi-attacher:${CSI_ATTACHER_TAG}
          args:
            - "--v=5"
            - "--csi-address=\$(ADDRESS)"
            - "--timeout=3m"
          resources:
            requests:
              cpu: 20m
          env:
            - name: ADDRESS
              value: /var/lib/csi/sockets/pluginproxy/csi.sock
          imagePullPolicy: "IfNotPresent"
          volumeMounts:
            - name: socket-dir
              mountPath: /var/lib/csi/sockets/pluginproxy/
        - name: csi-provisioner
          image: ${CONTAINER_INFRA_PREFIX:-quay.io/k8scsi/}csi-provisioner:${CSI_PROVISIONER_TAG}
          args:
            - "--csi-address=\$(ADDRESS)"
            - "--timeout=3m"
          resources:
            requests:
              cpu: 20m
          env:
            - name: ADDRESS
              value: /var/lib/csi/sockets/pluginproxy/csi.sock
          imagePullPolicy: "IfNotPresent"
          volumeMounts:
            - name: socket-dir
              mountPath: /var/lib/csi/sockets/pluginproxy/
        - name: csi-snapshotter
          image: ${CONTAINER_INFRA_PREFIX:-quay.io/k8scsi/}csi-snapshotter:${CSI_SNAPSHOTTER_TAG}
          args:
            - "--csi-address=\$(ADDRESS)"
          resources:
            requests:
              cpu: 20m
          env:
            - name: ADDRESS
              value: /var/lib/csi/sockets/pluginproxy/csi.sock
          imagePullPolicy: Always
          volumeMounts:
            - mountPath: /var/lib/csi/sockets/pluginproxy/
              name: socket-dir
        - name: csi-resizer
          image: ${CONTAINER_INFRA_PREFIX:-quay.io/k8scsi/}csi-resizer:${CSI_RESIZER_TAG}
          args:
            - "--v=5"
            - "--csi-address=\$(ADDRESS)"
          resources:
            requests:
              cpu: 20m
          env:
            - name: ADDRESS
              value: /var/lib/csi/sockets/pluginproxy/csi.sock
          imagePullPolicy: "IfNotPresent"
          volumeMounts:
            - name: socket-dir
              mountPath: /var/lib/csi/sockets/pluginproxy/
        - name: cinder-csi-plugin
          image: ${CONTAINER_INFRA_PREFIX:-docker.io/k8scloudprovider/}cinder-csi-plugin:${CINDER_CSI_PLUGIN_TAG}
          args :
            - /bin/cinder-csi-plugin
            - "--nodeid=\$(NODE_ID)"
            - "--endpoint=\$(CSI_ENDPOINT)"
            - "--cloud-config=\$(CLOUD_CONFIG)"
            - "--cluster=\$(CLUSTER_NAME)"
          resources:
            requests:
              cpu: 20m
          env:
            - name: NODE_ID
              valueFrom:
                fieldRef:
                  fieldPath: spec.nodeName
            - name: CSI_ENDPOINT
              value: unix://csi/csi.sock
            - name: CLOUD_CONFIG
              value: /etc/config/cloud-config
            - name: CLUSTER_NAME
              value: kubernetes
          imagePullPolicy: "IfNotPresent"
          volumeMounts:
            - name: socket-dir
              mountPath: /csi
            - name: secret-cinderplugin
              mountPath: /etc/config
              readOnly: true
            - name: cacert
              mountPath: /etc/kubernetes/ca-bundle.crt
              readOnly: true
      volumes:
        - name: socket-dir
          emptyDir:
        - name: secret-cinderplugin
          secret:
            secretName: cinder-csi-cloud-config
        - name: cacert
          hostPath:
            path: /etc/kubernetes/ca-bundle.crt
            type: File
---
# This YAML defines all API objects to create RBAC roles for csi node plugin.
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: csi-cinder-node-sa
  namespace: kube-system
---
kind: ClusterRole
apiVersion: rbac.authorization.k8s.io/v1
metadata:
  name: csi-nodeplugin-role
rules:
  - apiGroups: [""]
    resources: ["events"]
    verbs: ["get", "list", "watch", "create", "update", "patch"]
---
kind: ClusterRoleBinding
apiVersion: rbac.authorization.k8s.io/v1
metadata:
  name: csi-nodeplugin-binding
subjects:
  - kind: ServiceAccount
    name: csi-cinder-node-sa
    namespace: kube-system
roleRef:
  kind: ClusterRole
  name: csi-nodeplugin-role
  apiGroup: rbac.authorization.k8s.io
---
# This YAML file contains driver-registrar & csi driver nodeplugin API objects,
# which are necessary to run csi nodeplugin for cinder.
---
kind: DaemonSet
apiVersion: apps/v1
metadata:
  name: csi-cinder-nodeplugin
  namespace: kube-system
spec:
  selector:
    matchLabels:
      app: csi-cinder-nodeplugin
  template:
    metadata:
      labels:
        app: csi-cinder-nodeplugin
    spec:
      tolerations:
        - operator: Exists
      serviceAccount: csi-cinder-node-sa
      hostNetwork: true
      containers:
        - name: node-driver-registrar
          image: ${CONTAINER_INFRA_PREFIX:-quay.io/k8scsi/}csi-node-driver-registrar:${CSI_NODE_DRIVER_REGISTRAR_TAG}
          args:
            - "--csi-address=\$(ADDRESS)"
            - "--kubelet-registration-path=\$(DRIVER_REG_SOCK_PATH)"
          resources:
            requests:
              cpu: 25m
          lifecycle:
            preStop:
              exec:
                command: ["/bin/sh", "-c", "rm -rf /registration/cinder.csi.openstack.org /registration/cinder.csi.openstack.org-reg.sock"]
          env:
            - name: ADDRESS
              value: /csi/csi.sock
            - name: DRIVER_REG_SOCK_PATH
              value: /var/lib/kubelet/plugins/cinder.csi.openstack.org/csi.sock
            - name: KUBE_NODE_NAME
              valueFrom:
                fieldRef:
                  fieldPath: spec.nodeName
          imagePullPolicy: "IfNotPresent"
          volumeMounts:
            - name: socket-dir
              mountPath: /csi
            - name: registration-dir
              mountPath: /registration
        - name: cinder-csi-plugin
          securityContext:
            privileged: true
            capabilities:
              add: ["SYS_ADMIN"]
            allowPrivilegeEscalation: true
          image: ${CONTAINER_INFRA_PREFIX:-docker.io/k8scloudprovider/}cinder-csi-plugin:${CINDER_CSI_PLUGIN_TAG}
          args :
            - /bin/cinder-csi-plugin
            - "--nodeid=\$(NODE_ID)"
            - "--endpoint=\$(CSI_ENDPOINT)"
            - "--cloud-config=\$(CLOUD_CONFIG)"
          resources:
            requests:
              cpu: 25m
          env:
            - name: NODE_ID
              valueFrom:
                fieldRef:
                  fieldPath: spec.nodeName
            - name: CSI_ENDPOINT
              value: unix://csi/csi.sock
            - name: CLOUD_CONFIG
              value: /etc/config/cloud-config
          imagePullPolicy: "IfNotPresent"
          volumeMounts:
            - name: socket-dir
              mountPath: /csi
            - name: kubelet-dir
              mountPath: /var/lib/kubelet
              mountPropagation: "Bidirectional"
            - name: pods-cloud-data
              mountPath: /var/lib/cloud/data
              readOnly: true
            - name: pods-probe-dir
              mountPath: /dev
              mountPropagation: "HostToContainer"
            - name: secret-cinderplugin
              mountPath: /etc/config
              readOnly: true
            - name: cacert
              mountPath: /etc/kubernetes/ca-bundle.crt
              readOnly: true
      volumes:
        - name: socket-dir
          hostPath:
            path: /var/lib/kubelet/plugins/cinder.csi.openstack.org
            type: DirectoryOrCreate
        - name: registration-dir
          hostPath:
            path: /var/lib/kubelet/plugins_registry/
            type: Directory
        - name: kubelet-dir
          hostPath:
            path: /var/lib/kubelet
            type: Directory
        - name: pods-cloud-data
          hostPath:
            path: /var/lib/cloud/data
        - name: pods-probe-dir
          hostPath:
            path: /dev
            type: Directory
        - name: secret-cinderplugin
          secret:
            secretName: cinder-csi-cloud-config
        - name: cacert
          hostPath:
            path: /etc/kubernetes/ca-bundle.crt
            type: File
---
apiVersion: storage.k8s.io/v1
kind: CSIDriver
metadata:
  name: cinder.csi.openstack.org
spec:
  attachRequired: true
  podInfoOnMount: true
  volumeLifecycleModes:
  - Persistent
  - Ephemeral
EOF

    echo "Waiting for Kubernetes API..."
    until  [ "ok" = "$(kubectl get --raw='/healthz')" ]
    do
        sleep 5
    done

    cat <<EOF | kubectl apply -f -
---
apiVersion: v1
kind: Secret
metadata:
  name: cinder-csi-cloud-config
  namespace: kube-system
type: Opaque
stringData:
  cloud-config: |-
    [Global]
    auth-url=$AUTH_URL
    user-id=$TRUSTEE_USER_ID
    password=$TRUSTEE_PASSWORD
    trust-id=$TRUST_ID
    region=$REGION_NAME
    ca-file=/etc/kubernetes/ca-bundle.crt
EOF

    kubectl apply -f ${CINDER_CSI_DEPLOY}
fi
printf "Finished running ${step}\n"
