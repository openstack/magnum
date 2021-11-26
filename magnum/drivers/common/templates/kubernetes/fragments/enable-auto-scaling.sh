step="enable-auto-scaling"
printf "Starting to run ${step}\n"

. /etc/sysconfig/heat-params

_docker_ca_prefix=${CONTAINER_INFRA_PREFIX:-docker.io/openstackmagnum/}

auto_scaling_enabled=$(echo $AUTO_SCALING_ENABLED | tr '[:upper:]' '[:lower:]')
auto_healing_enabled=$(echo $AUTO_HEALING_ENABLED | tr '[:upper:]' '[:lower:]')
autohealing_controller=$(echo ${AUTO_HEALING_CONTROLLER} | tr '[:upper:]' '[:lower:]')

if [[ "${auto_scaling_enabled}" = "true" || ("${auto_healing_enabled}" = "true" && "${autohealing_controller}" = "draino") ]]; then
    # Generate Autoscaler manifest file
    AUTOSCALER_DEPLOY=/srv/magnum/kubernetes/manifests/autoscaler.yaml

    [ -f ${AUTOSCALER_DEPLOY} ] || {
        echo "Writing File: $AUTOSCALER_DEPLOY"
        mkdir -p $(dirname ${AUTOSCALER_DEPLOY})
        cat << EOF > ${AUTOSCALER_DEPLOY}
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: cluster-autoscaler-role
rules:
  - apiGroups: ["coordination.k8s.io"]
    resources: ["leases"]
    verbs: ["create"]
  - apiGroups: ["coordination.k8s.io"]
    resources: ["leases"]
    resourceNames: ["cluster-autoscaler"]
    verbs: ["get", "update", "patch", "delete"]
  # TODO: remove in 1.18; CA uses lease objects for leader election since 1.17
  - apiGroups: [""]
    resources: ["endpoints"]
    verbs: ["create"]
  - apiGroups: [""]
    resources: ["endpoints"]
    resourceNames: ["cluster-autoscaler"]
    verbs: ["get", "update", "patch", "delete"]
  # accessing & modifying cluster state (nodes & pods)
  - apiGroups: [""]
    resources: ["nodes"]
    verbs: ["get", "list", "watch", "update", "patch"]
  - apiGroups: [""]
    resources: ["pods"]
    verbs: ["get", "list", "watch"]
  - apiGroups: [""]
    resources: ["pods/eviction"]
    verbs: ["create"]
  # read-only access to cluster state
  - apiGroups: [""]
    resources: ["services", "replicationcontrollers", "persistentvolumes", "persistentvolumeclaims"]
    verbs: ["get", "list", "watch"]
  - apiGroups: ["apps"]
    resources: ["daemonsets", "replicasets"]
    verbs: ["get", "list", "watch"]
  - apiGroups: ["apps"]
    resources: ["statefulsets"]
    verbs: ["get", "list", "watch"]
  - apiGroups: ["batch"]
    resources: ["jobs"]
    verbs: ["get", "list", "watch"]
  - apiGroups: ["policy"]
    resources: ["poddisruptionbudgets"]
    verbs: ["get", "list", "watch"]
  - apiGroups: ["storage.k8s.io"]
    resources: ["storageclasses", "csinodes"]
    verbs: ["get", "list", "watch"]
  # misc access
  - apiGroups: [""]
    resources: ["events"]
    verbs: ["create", "update", "patch"]
  - apiGroups: [""]
    resources: ["configmaps"]
    verbs: ["create"]
  - apiGroups: [""]
    resources: ["configmaps"]
    resourceNames: ["cluster-autoscaler-status"]
    verbs: ["get", "update", "patch", "delete"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: cluster-autoscaler-rolebinding
  namespace: kube-system
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: cluster-autoscaler-role
subjects:
  - kind: ServiceAccount
    name: cluster-autoscaler-account
    namespace: kube-system
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: cluster-autoscaler-account
  namespace: kube-system
---
kind: Deployment
apiVersion: apps/v1
metadata:
  name: cluster-autoscaler
  namespace: kube-system
  labels:
    app: cluster-autoscaler
spec:
  replicas: 1
  selector:
    matchLabels:
      app: cluster-autoscaler
  template:
    metadata:
      namespace: kube-system
      labels:
        app: cluster-autoscaler
    spec:
      nodeSelector:
        node-role.kubernetes.io/master: ""
      securityContext:
        runAsUser: 1001
      tolerations:
        - effect: NoSchedule
          operator: Exists
        - key: CriticalAddonsOnly
          operator: Exists
        - effect: NoExecute
          operator: Exists
        - key: node.cloudprovider.kubernetes.io/uninitialized
          value: "true"
          effect: NoSchedule
        - key: node-role.kubernetes.io/master
          effect: NoSchedule
      serviceAccountName: cluster-autoscaler-account
      containers:
        - name: cluster-autoscaler
          image: ${_docker_ca_prefix}cluster-autoscaler:${AUTOSCALER_TAG}
          imagePullPolicy: Always
          command:
            - ./cluster-autoscaler
            - --alsologtostderr
            - --cloud-provider=magnum
            - --cluster-name=${CLUSTER_UUID}
            - --cloud-config=/config/cloud-config
            - --nodes=${MIN_NODE_COUNT}:${MAX_NODE_COUNT}:default-worker
            - --scale-down-unneeded-time=10m
            - --scale-down-delay-after-failure=3m
            - --scale-down-delay-after-add=10m
          resources:
            requests:
              cpu: 100m
              memory: 300Mi
          ports:
          - containerPort: 8085
            name: metrics
            protocol: TCP
          volumeMounts:
            - name: ca-bundle
              mountPath: /etc/kubernetes
              readOnly: true
            - name: cloud-config
              mountPath: /config
              readOnly: true
      volumes:
        - name: ca-bundle
          secret:
            secretName: ca-bundle
        - name: cloud-config
          secret:
            secretName: cluster-autoscaler-cloud-config
EOF
    }

    echo "Waiting for Kubernetes API..."
    until  [ "ok" = "$(kubectl get --raw='/healthz')" ]
    do
        sleep 5
    done

    kubectl create secret generic ca-bundle --from-file=/etc/kubernetes/ca-bundle.crt -n kube-system

    cat <<EOF | kubectl apply -f -
---
apiVersion: v1
kind: Secret
metadata:
  name: cluster-autoscaler-cloud-config
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

    kubectl apply -f ${AUTOSCALER_DEPLOY}
fi
printf "Finished running ${step}\n"
