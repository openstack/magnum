#!/bin/sh -x

. /etc/sysconfig/heat-params

# NOTE(flwang): Let's keep the same addons yaml file on all masters,
# but if it's not the primary/bootstrapping master, don't try to
# create those resources to avoid race condition issue until the
# kubectl issue https://github.com/kubernetes/kubernetes/issues/44165
# fixed.
if [ "$MASTER_INDEX" != "0" ]; then
    exit 0
fi

echo "Waiting for Kubernetes API..."
until curl --silent "http://127.0.0.1:8080/version"
do
    sleep 5
done

cat <<EOF | kubectl apply --validate=false -f -
apiVersion: rbac.authorization.k8s.io/v1beta1
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

cat <<EOF | kubectl apply --validate=false -f -
apiVersion: rbac.authorization.k8s.io/v1beta1
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
apiVersion: rbac.authorization.k8s.io/v1beta1
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
