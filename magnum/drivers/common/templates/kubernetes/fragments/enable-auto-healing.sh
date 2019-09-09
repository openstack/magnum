#!/bin/sh

step="enable-node-problem-detector"
printf "Starting to run ${step}\n"

. /etc/sysconfig/heat-params

_gcr_prefix=${CONTAINER_INFRA_PREFIX:-k8s.gcr.io/}

# Generate Node Problem Detector manifest file
NPD_DEPLOY=/srv/magnum/kubernetes/manifests/npd.yaml

[ -f ${NPD_DEPLOY} ] || {
    echo "Writing File: $NPD_DEPLOY"
    mkdir -p $(dirname ${NPD_DEPLOY})
    cat << EOF > ${NPD_DEPLOY}
apiVersion: v1
kind: ServiceAccount
metadata:
  name: node-problem-detector
  namespace: kube-system
  labels:
    kubernetes.io/cluster-service: "true"
    addonmanager.kubernetes.io/mode: Reconcile
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: magnum:podsecuritypolicy:node-problem-detector
  namespace: kube-system
  labels:
    addonmanager.kubernetes.io/mode: Reconcile
    kubernetes.io/cluster-service: "true"
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: magnum:podsecuritypolicy:privileged
subjects:
- kind: ServiceAccount
  name: node-problem-detector
  namespace: kube-system
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: npd-binding
  labels:
    kubernetes.io/cluster-service: "true"
    addonmanager.kubernetes.io/mode: Reconcile
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: system:node-problem-detector
subjects:
- kind: ServiceAccount
  name: node-problem-detector
  namespace: kube-system
---
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: npd
  namespace: kube-system
  labels:
    k8s-app: node-problem-detector
    version: ${NODE_PROBLEM_DETECTOR_TAG}
    kubernetes.io/cluster-service: "true"
    addonmanager.kubernetes.io/mode: Reconcile
spec:
  selector:
    matchLabels:
      k8s-app: node-problem-detector
      version: ${NODE_PROBLEM_DETECTOR_TAG}
  template:
    metadata:
      labels:
        k8s-app: node-problem-detector
        version: ${NODE_PROBLEM_DETECTOR_TAG}
        kubernetes.io/cluster-service: "true"
    spec:
      containers:
      - name: node-problem-detector
        image: ${_gcr_prefix}node-problem-detector:${NODE_PROBLEM_DETECTOR_TAG}
        command:
        - "/bin/sh"
        - "-c"
        # Pass both config to support both journald and syslog.
        - "exec /node-problem-detector --logtostderr --system-log-monitors=/config/kernel-monitor.json,/config/kernel-monitor-filelog.json,/config/docker-monitor.json,/config/docker-monitor-filelog.json 2>&1 | tee /var/log/node-problem-detector.log"
        securityContext:
          privileged: true
        resources:
          limits:
            cpu: "200m"
            memory: "100Mi"
          requests:
            cpu: "20m"
            memory: "20Mi"
        env:
        - name: NODE_NAME
          valueFrom:
            fieldRef:
              fieldPath: spec.nodeName
        volumeMounts:
        - name: log
          mountPath: /var/log
        - name: localtime
          mountPath: /etc/localtime
          readOnly: true
      volumes:
      - name: log
        hostPath:
          path: /var/log/
      - name: localtime
        hostPath:
          path: /etc/localtime
          type: "FileOrCreate"
      serviceAccountName: node-problem-detector
      tolerations:
      - operator: "Exists"
        effect: "NoExecute"
      - key: "CriticalAddonsOnly"
        operator: "Exists"
EOF
}

echo "Waiting for Kubernetes API..."
until  [ "ok" = "$(curl --silent http://127.0.0.1:8080/healthz)" ]
do
    sleep 5
done

kubectl apply -f ${NPD_DEPLOY}

printf "Finished running ${step}\n"

_docker_draino_prefix=${CONTAINER_INFRA_PREFIX:-docker.io/planetlabs/}
step="enable-auto-healing"
printf "Starting to run ${step}\n"

if [ "$(echo $AUTO_HEALING_ENABLED | tr '[:upper:]' '[:lower:]')" = "true" ]; then
    # Generate Draino manifest file
    DRAINO_DEPLOY=/srv/magnum/kubernetes/manifests/draino.yaml

    [ -f ${DRAINO_DEPLOY} ] || {
        echo "Writing File: $DRAINO_DEPLOY"
        mkdir -p $(dirname ${DRAINO_DEPLOY})
        cat << EOF > ${DRAINO_DEPLOY}
---
apiVersion: v1
kind: ServiceAccount
metadata:
  labels: {component: draino}
  name: draino
  namespace: kube-system
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  labels: {component: draino}
  name: draino
rules:
- apiGroups: ['']
  resources: [events]
  verbs: [create, patch, update]
- apiGroups: ['']
  resources: [nodes]
  verbs: [get, watch, list, update]
- apiGroups: ['']
  resources: [nodes/status]
  verbs: [patch]
- apiGroups: ['']
  resources: [pods]
  verbs: [get, watch, list]
- apiGroups: ['']
  resources: [pods/eviction]
  verbs: [create]
- apiGroups: [extensions]
  resources: [daemonsets]
  verbs: [get, watch, list]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  labels: {component: draino}
  name: draino
roleRef: {apiGroup: rbac.authorization.k8s.io, kind: ClusterRole, name: draino}
subjects:
- {kind: ServiceAccount, name: draino, namespace: kube-system}
---
apiVersion: apps/v1
kind: Deployment
metadata:
  labels: {component: draino}
  name: draino
  namespace: kube-system
spec:
  # Draino does not currently support locking/master election, so you should
  # only run one draino at a time. Draino won't start draining nodes immediately
  # so it's usually safe for multiple drainos to exist for a brief period of
  # time.
  replicas: 1
  selector:
    matchLabels: {component: draino}
  template:
    metadata:
      labels: {component: draino}
      name: draino
      namespace: kube-system
    spec:
      nodeSelector:
        node-role.kubernetes.io/master: ""
      hostNetwork: true
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
      containers:
      # You'll want to change these labels and conditions to suit your deployment.
      - command: [/draino, --node-label=draino-enabled=true, --evict-daemonset-pods, --evict-emptydir-pods, NotReady]
        image: ${_docker_draino_prefix}draino:${DRAINO_TAG}
        livenessProbe:
          httpGet: {path: /healthz, port: 10002}
          initialDelaySeconds: 30
        name: draino
      serviceAccountName: draino
EOF
    }

    kubectl apply -f ${DRAINO_DEPLOY}

fi
printf "Finished running ${step}\n"
