# octavia-ingress-controller RBAC
OCTAVIA_INGRESS_CONTROLLER_RBAC=/srv/magnum/kubernetes/manifests/octavia-ingress-controller-rbac.yaml
OCTAVIA_INGRESS_CONTROLLER_RBAC_CONTENT=$(cat <<EOF
---
kind: ServiceAccount
apiVersion: v1
metadata:
  name: octavia-ingress-controller
  namespace: kube-system
---
kind: ClusterRoleBinding
apiVersion: rbac.authorization.k8s.io/v1
metadata:
  name: octavia-ingress-controller
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: cluster-admin
subjects:
  - kind: ServiceAccount
    name: octavia-ingress-controller
    namespace: kube-system
EOF
)
writeFile $OCTAVIA_INGRESS_CONTROLLER_RBAC "$OCTAVIA_INGRESS_CONTROLLER_RBAC_CONTENT"

# octavia-ingress-controller config file
OCTAVIA_INGRESS_CONTROLLER_CONFIGMAP=/srv/magnum/kubernetes/manifests/octavia-ingress-controller-config.yaml
OCTAVIA_INGRESS_CONTROLLER_CONFIGMAP_CONTENT=$(cat <<EOF
---
kind: ConfigMap
apiVersion: v1
metadata:
  name: octavia-ingress-controller-config
  namespace: kube-system
data:
  config: |
    cluster-name: ${CLUSTER_UUID}
    openstack:
      auth-url: ${AUTH_URL}
      user-id: ${TRUSTEE_USER_ID}
      password: ${TRUSTEE_PASSWORD}
      trust-id: ${TRUST_ID}
      region: ${REGION_NAME}
      ca-file: /etc/kubernetes/ca-bundle.crt
    octavia:
      subnet-id: ${CLUSTER_SUBNET}
      floating-network-id: ${EXTERNAL_NETWORK_ID}
EOF
)
writeFile $OCTAVIA_INGRESS_CONTROLLER_CONFIGMAP "$OCTAVIA_INGRESS_CONTROLLER_CONFIGMAP_CONTENT"

# octavia-ingress-controller deployment
oic_image="${CONTAINER_INFRA_PREFIX:-registry.k8s.io/provider-os/}octavia-ingress-controller:${OCTAVIA_INGRESS_CONTROLLER_TAG}"
OCTAVIA_INGRESS_CONTROLLER=/srv/magnum/kubernetes/manifests/octavia-ingress-controller.yaml
OCTAVIA_INGRESS_CONTROLLER_CONTENT=$(cat <<EOF
---
kind: StatefulSet
apiVersion: apps/v1
metadata:
  name: octavia-ingress-controller
  namespace: kube-system
  labels:
    k8s-app: octavia-ingress-controller
spec:
  replicas: 1
  selector:
    matchLabels:
      k8s-app: octavia-ingress-controller
  template:
    metadata:
      labels:
        k8s-app: octavia-ingress-controller
    spec:
      serviceAccountName: octavia-ingress-controller
      tolerations:
        - effect: NoSchedule # Make sure the pod can be scheduled on master kubelet.
          operator: Exists
        - key: CriticalAddonsOnly # Mark the pod as a critical add-on for rescheduling.
          operator: Exists
        - effect: NoExecute
          operator: Exists
      nodeSelector:
        node-role.kubernetes.io/master: "" # octavia-ingress-controller needs to access /etc/kubernetes folder.
      containers:
        - name: octavia-ingress-controller
          image: ${oic_image}
          imagePullPolicy: IfNotPresent
          args:
            - /bin/octavia-ingress-controller
            - --config=/etc/config/octavia-ingress-controller-config.yaml
          resources:
            requests:
              cpu: 50m
          volumeMounts:
            - mountPath: /etc/kubernetes
              name: kubernetes-config
              readOnly: true
            - name: ingress-config
              mountPath: /etc/config
      hostNetwork: true
      volumes:
        - name: kubernetes-config
          hostPath:
            path: /etc/kubernetes
            type: Directory
        - name: ingress-config
          configMap:
            name: octavia-ingress-controller-config
            items:
              - key: config
                path: octavia-ingress-controller-config.yaml
EOF
)
writeFile $OCTAVIA_INGRESS_CONTROLLER "$OCTAVIA_INGRESS_CONTROLLER_CONTENT"

echo "Waiting for Kubernetes API..."
until  [ "ok" = "$(kubectl get --raw='/healthz')" ]
do
    sleep 5
done

kubectl apply --validate=false -f $OCTAVIA_INGRESS_CONTROLLER_RBAC
kubectl apply --validate=false -f $OCTAVIA_INGRESS_CONTROLLER_CONFIGMAP
kubectl apply --validate=false -f $OCTAVIA_INGRESS_CONTROLLER
