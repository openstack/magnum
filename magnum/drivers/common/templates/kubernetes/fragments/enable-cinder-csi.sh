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
# This YAML file contains RBAC API objects,
# which are necessary to run csi controller plugin

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
    verbs: ["get", "list", "watch", "patch"]
  - apiGroups: ["storage.k8s.io"]
    resources: ["csinodes"]
    verbs: ["get", "list", "watch"]
  - apiGroups: ["storage.k8s.io"]
    resources: ["volumeattachments"]
    verbs: ["get", "list", "watch", "patch"]
  - apiGroups: ["storage.k8s.io"]
    resources: ["volumeattachments/status"]
    verbs: ["patch"]
  - apiGroups: ["coordination.k8s.io"]
    resources: ["leases"]
    verbs: ["get", "watch", "list", "delete", "update", "create"]

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
  - apiGroups: ["storage.k8s.io"]
    resources: ["volumeattachments"]
    verbs: ["get", "list", "watch"]
  - apiGroups: ["coordination.k8s.io"]
    resources: ["leases"]
    verbs: ["get", "watch", "list", "delete", "update", "create"]
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
    resources: ["events"]
    verbs: ["list", "watch", "create", "update", "patch"]
  # Secret permission is optional.
  # Enable it if your driver needs secret.
  # For example, `csi.storage.k8s.io/snapshotter-secret-name` is set in VolumeSnapshotClass.
  # See https://kubernetes-csi.github.io/docs/secrets-and-credentials.html for more details.
  #  - apiGroups: [""]
  #    resources: ["secrets"]
  #    verbs: ["get", "list"]
  - apiGroups: ["snapshot.storage.k8s.io"]
    resources: ["volumesnapshotclasses"]
    verbs: ["get", "list", "watch"]
  - apiGroups: ["snapshot.storage.k8s.io"]
    resources: ["volumesnapshotcontents"]
    verbs: ["create", "get", "list", "watch", "update", "delete", "patch"]
  - apiGroups: ["snapshot.storage.k8s.io"]
    resources: ["volumesnapshotcontents/status"]
    verbs: ["update", "patch"]
  - apiGroups: ["coordination.k8s.io"]
    resources: ["leases"]
    verbs: ["get", "watch", "list", "delete", "update", "create"]
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
    verbs: ["get", "list", "watch", "patch"]
  - apiGroups: [""]
    resources: ["persistentvolumeclaims"]
    verbs: ["get", "list", "watch"]
  - apiGroups: [""]
    resources: ["pods"]
    verbs: ["get", "list", "watch"]
  - apiGroups: [""]
    resources: ["persistentvolumeclaims/status"]
    verbs: ["patch"]
  - apiGroups: [""]
    resources: ["events"]
    verbs: ["list", "watch", "create", "update", "patch"]
  - apiGroups: ["coordination.k8s.io"]
    resources: ["leases"]
    verbs: ["get", "watch", "list", "delete", "update", "create"]
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
# This YAML file contains CSI Controller Plugin Sidecars
# external-attacher, external-provisioner, external-snapshotter
# external-resize, liveness-probe

kind: Deployment
apiVersion: apps/v1
metadata:
  name: csi-cinder-controllerplugin
  namespace: kube-system
spec:
  replicas: 1
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxUnavailable: 0
      maxSurge: 1
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
        node-role.kubernetes.io/control-plane: ""
      containers:
        - name: csi-attacher
          image: ${CONTAINER_INFRA_PREFIX:-k8s.gcr.io/sig-storage/}csi-attacher:${CSI_ATTACHER_TAG}
          args:
            - "--csi-address=\$(ADDRESS)"
            - "--timeout=3m"
            - "--leader-election=true"
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
          image: ${CONTAINER_INFRA_PREFIX:-k8s.gcr.io/sig-storage/}csi-provisioner:${CSI_PROVISIONER_TAG}
          args:
            - "--csi-address=\$(ADDRESS)"
            - "--timeout=3m"
            - "--default-fstype=ext4"
            - "--feature-gates=Topology=true"
            - "--extra-create-metadata"
            - "--leader-election=true"
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
          image: ${CONTAINER_INFRA_PREFIX:-k8s.gcr.io/sig-storage/}csi-snapshotter:${CSI_SNAPSHOTTER_TAG}
          args:
            - "--csi-address=\$(ADDRESS)"
            - "--timeout=3m"
            - "--extra-create-metadata"
            - "--leader-election=true"
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
          image: ${CONTAINER_INFRA_PREFIX:-k8s.gcr.io/sig-storage/}csi-resizer:${CSI_RESIZER_TAG}
          args:
            - "--csi-address=\$(ADDRESS)"
            - "--timeout=3m"
            - "--handle-volume-inuse-error=false"
            - "--leader-election=true"
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
        - name: liveness-probe
          image: ${CONTAINER_INFRA_PREFIX:-k8s.gcr.io/sig-storage/}livenessprobe:${CSI_LIVENESS_PROBE_TAG}
          args:
            - "--csi-address=\$(ADDRESS)"
          resources:
            requests:
              cpu: 20m
          env:
            - name: ADDRESS
              value: /var/lib/csi/sockets/pluginproxy/csi.sock
          volumeMounts:
            - mountPath: /var/lib/csi/sockets/pluginproxy/
              name: socket-dir
        - name: cinder-csi-plugin
          image: ${CONTAINER_INFRA_PREFIX:-registry.k8s.io/provider-os/}cinder-csi-plugin:${CINDER_CSI_PLUGIN_TAG}
          args:
            - /bin/cinder-csi-plugin
            - "--endpoint=\$(CSI_ENDPOINT)"
            - "--cloud-config=\$(CLOUD_CONFIG)"
            - "--cluster=\$(CLUSTER_NAME)"
          env:
            - name: CSI_ENDPOINT
              value: unix://csi/csi.sock
            - name: CLOUD_CONFIG
              value: /etc/config/cloud-config
            - name: CLUSTER_NAME
              value: kubernetes
          imagePullPolicy: "IfNotPresent"
          ports:
            - containerPort: 9808
              name: healthz
              protocol: TCP
          # The probe
          livenessProbe:
            failureThreshold: 5
            httpGet:
              path: /healthz
              port: healthz
            initialDelaySeconds: 10
            timeoutSeconds: 10
            periodSeconds: 60
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
          image: ${CONTAINER_INFRA_PREFIX:-k8s.gcr.io/sig-storage/}csi-node-driver-registrar:${CSI_NODE_DRIVER_REGISTRAR_TAG}
          args:
            - "--csi-address=\$(ADDRESS)"
            - "--kubelet-registration-path=\$(DRIVER_REG_SOCK_PATH)"
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
        - name: liveness-probe
          image: ${CONTAINER_INFRA_PREFIX:-k8s.gcr.io/sig-storage/}livenessprobe:${CSI_LIVENESS_PROBE_TAG}
          args:
            - --csi-address=/csi/csi.sock
          resources:
            requests:
              cpu: 20m
          volumeMounts:
            - name: socket-dir
              mountPath: /csi
        - name: cinder-csi-plugin
          securityContext:
            privileged: true
            capabilities:
              add: ["SYS_ADMIN"]
            allowPrivilegeEscalation: true
          image: ${CONTAINER_INFRA_PREFIX:-registry.k8s.io/provider-os/}cinder-csi-plugin:${CINDER_CSI_PLUGIN_TAG}
          args:
            - /bin/cinder-csi-plugin
            - "--endpoint=\$(CSI_ENDPOINT)"
            - "--cloud-config=\$(CLOUD_CONFIG)"
          env:
            - name: CSI_ENDPOINT
              value: unix://csi/csi.sock
            - name: CLOUD_CONFIG
              value: /etc/config/cloud-config
          imagePullPolicy: "IfNotPresent"
          ports:
            - containerPort: 9808
              name: healthz
              protocol: TCP
          # The probe
          livenessProbe:
            failureThreshold: 5
            httpGet:
              path: /healthz
              port: healthz
            initialDelaySeconds: 10
            timeoutSeconds: 3
            periodSeconds: 10
          volumeMounts:
            - name: socket-dir
              mountPath: /csi
            - name: kubelet-dir
              mountPath: /var/lib/kubelet
              mountPropagation: "Bidirectional"
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
