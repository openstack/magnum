. /etc/sysconfig/heat-params

step="enable-keystone-auth"
printf "Starting to run ${step}\n"

if [ "$(echo $KEYSTONE_AUTH_ENABLED | tr '[:upper:]' '[:lower:]')" != "false" ]; then
    _prefix=${CONTAINER_INFRA_PREFIX:-registry.k8s.io/provider-os/}
    CERT_DIR=/etc/kubernetes/certs

    # Create policy configmap for keystone auth
    KEYSTONE_AUTH_POLICY=/srv/magnum/kubernetes/keystone-auth-policy.yaml

    [ -f ${KEYSTONE_AUTH_POLICY} ] || {
        echo "Writing File: $KEYSTONE_AUTH_POLICY"
        mkdir -p $(dirname ${KEYSTONE_AUTH_POLICY})
        cat << EOF > ${KEYSTONE_AUTH_POLICY}
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: k8s-keystone-auth
  namespace: kube-system
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  labels:
    kubernetes.io/bootstrapping: rbac-defaults
  name: system:k8s-keystone-auth
rules:
- apiGroups:
  - ""
  resources:
  - configmaps
  - services
  - pods
  verbs:
  - get
  - list
  - watch
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  annotations:
    rbac.authorization.kubernetes.io/autoupdate: "true"
  labels:
    kubernetes.io/bootstrapping: rbac-defaults
  name: system:k8s-keystone-auth
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: system:k8s-keystone-auth
subjects:
- kind: ServiceAccount
  name: k8s-keystone-auth
  namespace: kube-system
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: k8s-keystone-auth-policy
  namespace: kube-system
data:
  policies: |
    $KEYSTONE_AUTH_DEFAULT_POLICY
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: keystone-sync-policy
  namespace: kube-system
data:
  syncConfig: |
    role-mappings:
      - keystone-role: member
        groups: []
EOF
    }

    # Generate k8s-keystone-auth service manifest file
    KEYSTONE_AUTH_DEPLOY=/srv/magnum/kubernetes/manifests/k8s-keystone-auth.yaml

    [ -f ${KEYSTONE_AUTH_DEPLOY} ] || {
        echo "Writing File: $KEYSTONE_AUTH_DEPLOY"
        mkdir -p $(dirname ${KEYSTONE_AUTH_DEPLOY})
        cat << EOF > ${KEYSTONE_AUTH_DEPLOY}
---
apiVersion: apps/v1
kind: DaemonSet
metadata:
  labels:
    component: k8s-keystone-auth
    tier: control-plane
  name: k8s-keystone-auth
  namespace: kube-system
spec:
  # The controllers can only have a single active instance.
  selector:
    matchLabels:
      k8s-app: k8s-keystone-auth
  template:
    metadata:
      name: k8s-keystone-auth
      namespace: kube-system
      labels:
        k8s-app: k8s-keystone-auth
    spec:
      serviceAccountName: k8s-keystone-auth
      tolerations:
        # Make sure the pod can be scheduled on master kubelet.
        - effect: NoSchedule
          operator: Exists
        # Mark the pod as a critical add-on for rescheduling.
        - key: CriticalAddonsOnly
          operator: Exists
        - effect: NoExecute
          operator: Exists
      nodeSelector:
        node-role.kubernetes.io/control-plane: ""
      containers:
        - name: k8s-keystone-auth
          image: ${_prefix}k8s-keystone-auth:${K8S_KEYSTONE_AUTH_TAG}
          imagePullPolicy: Always
          args:
            - ./bin/k8s-keystone-auth
            - --tls-cert-file
            - ${CERT_DIR}/server.crt
            - --tls-private-key-file
            - ${CERT_DIR}/server.key
            - --policy-configmap-name
            - k8s-keystone-auth-policy
            - --keystone-url
            - ${AUTH_URL}
            - --sync-configmap-name
            - keystone-sync-policy
            - --keystone-ca-file
            - /etc/kubernetes/ca-bundle.crt
            - --listen
            - 127.0.0.1:8443
          volumeMounts:
            - mountPath: ${CERT_DIR}
              name: k8s-certs
              readOnly: true
            - mountPath: /etc/kubernetes
              name: ca-certs
              readOnly: true
          resources:
            requests:
              cpu: 200m
          ports:
            - containerPort: 8443
              hostPort: 8443
              name: https
              protocol: TCP
      hostNetwork: true
      volumes:
        - hostPath:
            path: ${CERT_DIR}
            type: DirectoryOrCreate
          name: k8s-certs
        - hostPath:
            path: /etc/kubernetes
            type: DirectoryOrCreate
          name: ca-certs
EOF
    }

    until  [ "ok" = "$(kubectl get --raw='/healthz')" ]
    do
        echo "Waiting for Kubernetes API..."
        sleep 5
    done

    /usr/bin/kubectl apply -f ${KEYSTONE_AUTH_POLICY}
    /usr/bin/kubectl apply -f ${KEYSTONE_AUTH_DEPLOY}

fi

printf "Finished running ${step}\n"
