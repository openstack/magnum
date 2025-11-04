#!/bin/sh

step="kube-apiserver-to-kubelet-role"
printf "Starting to run ${step}\n"

set +x
. /etc/sysconfig/heat-params

set -x

ssh_cmd="ssh -F /srv/magnum/.ssh/config root@localhost"

until  [ "ok" = "$(kubectl get --raw='/healthz' 2>nil)" ]
do
    echo "Waiting for Kubernetes API..."
    sleep 5
done

cat <<EOF | $ssh_cmd kubectl apply --validate=false -f -
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  annotations:
    rbac.authorization.kubernetes.io/autoupdate: "true"
  labels:
    kubernetes.io/bootstrapping: rbac-defaults
  name: system:kube-apiserver-to-kubelet
rules:
  - apiGroups:
      - ""
    resources:
      - nodes/proxy
      - nodes/stats
      - nodes/log
      - nodes/spec
      - nodes/metrics
    verbs:
      - "*"
EOF

cat <<EOF | $ssh_cmd kubectl apply --validate=false -f -
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: system:kube-apiserver
  namespace: ""
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: system:kube-apiserver-to-kubelet
subjects:
  - apiGroup: rbac.authorization.k8s.io
    kind: User
    name: kubernetes
EOF

# Create an admin user and give it the cluster role.
ADMIN_RBAC=/srv/magnum/kubernetes/kubernetes-admin-rbac.yaml

[ -f ${ADMIN_RBAC} ] || {
    echo "Writing File: $ADMIN_RBAC"
    mkdir -p $(dirname ${ADMIN_RBAC})
    cat << EOF > ${ADMIN_RBAC}
apiVersion: v1
kind: ServiceAccount
metadata:
  name: admin
  namespace: kube-system
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: admin
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: cluster-admin
subjects:
- kind: ServiceAccount
  name: admin
  namespace: kube-system
EOF
}
kubectl apply --validate=false -f ${ADMIN_RBAC}

POD_SECURITY_POLICIES=/srv/magnum/kubernetes/podsecuritypolicies.yaml
# Pod Security Policies
[ -f ${POD_SECURITY_POLICIES} ] || {
    echo "Writing File: $POD_SECURITY_POLICIES"
    mkdir -p $(dirname ${POD_SECURITY_POLICIES})
    cat > ${POD_SECURITY_POLICIES} <<EOF
---
apiVersion: policy/v1beta1
kind: PodSecurityPolicy
metadata:
  name: magnum.privileged
  annotations:
    kubernetes.io/description: 'privileged allows full unrestricted access to
      pod features, as if the PodSecurityPolicy controller was not enabled.'
    seccomp.security.alpha.kubernetes.io/allowedProfileNames: '*'
  labels:
    kubernetes.io/cluster-service: "true"
    addonmanager.kubernetes.io/mode: Reconcile
spec:
  privileged: true
  allowPrivilegeEscalation: true
  allowedCapabilities:
  - '*'
  volumes:
  - '*'
  hostNetwork: true
  hostPorts:
  - min: 0
    max: 65535
  hostIPC: true
  hostPID: true
  runAsUser:
    rule: 'RunAsAny'
  seLinux:
    rule: 'RunAsAny'
  supplementalGroups:
    rule: 'RunAsAny'
  fsGroup:
    rule: 'RunAsAny'
  readOnlyRootFilesystem: false
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: magnum:podsecuritypolicy:privileged
  labels:
    kubernetes.io/cluster-service: "true"
    addonmanager.kubernetes.io/mode: Reconcile
rules:
- apiGroups:
  - policy
  resourceNames:
  - magnum.privileged
  resources:
  - podsecuritypolicies
  verbs:
  - use
EOF
}
#kubectl apply -f ${POD_SECURITY_POLICIES}

# Add the openstack trustee as a secret under kube-system
# Check if the secret 'os-trustee' already exists
if ! $ssh_cmd kubectl -n kube-system get secret os-trustee >/dev/null 2>&1; then
  # If it doesn't exist, create it
  $ssh_cmd kubectl -n kube-system create secret generic os-trustee \
      --from-literal=os-authURL=${AUTH_URL} \
      --from-literal=os-trustID=${TRUST_ID} \
      --from-literal=os-trusteeID=${TRUSTEE_USER_ID} \
      --from-literal=os-trusteePassword=${TRUSTEE_PASSWORD} \
      --from-literal=os-region=${REGION_NAME} \
      --from-file=os-certAuthority=/etc/kubernetes/ca-bundle.crt
else
  echo "Secret 'os-trustee' already exists. Skipping creation..."
fi

# Assgin read daemonset/replicaset/statefulset permssion to allow node drain itself
cat <<EOF | $ssh_cmd kubectl apply --validate=false -f -
---
apiVersion: v1
items:
- apiVersion: rbac.authorization.k8s.io/v1
  kind: ClusterRole
  metadata:
    name: system:node-drainer
  rules:
  - apiGroups:
    - ""
    resources:
    - pods/eviction
    verbs:
    - create
  - apiGroups:
    - apps
    resources:
    - statefulsets
    - daemonsets
    verbs:
    - get
    - list
  - apiGroups:
    - extensions
    resources:
    - daemonsets
    verbs:
    - get
    - list
- apiVersion: rbac.authorization.k8s.io/v1
  kind: ClusterRoleBinding
  metadata:
    name: system:node-drainer
  roleRef:
    apiGroup: rbac.authorization.k8s.io
    kind: ClusterRole
    name: system:node-drainer
  subjects:
  - apiGroup: rbac.authorization.k8s.io
    kind: Group
    name: system:nodes
kind: List
metadata: {}
EOF

# Post install file to setup some cloud provider/vendor specific configs
if [ "$POST_INSTALL_MANIFEST_URL" != "" ]; then
    $ssh_cmd kubectl apply -f "$POST_INSTALL_MANIFEST_URL"
fi

printf "Finished running ${step}\n"
