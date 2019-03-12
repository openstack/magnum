#!/bin/sh

step="enable-auto-healing"
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
        - "exec /node-problem-detector --logtostderr --system-log-monitors=/config/kernel-monitor.json,/config/kernel-monitor-filelog.json,/config/docker-monitor.json,/config/docker-monitor-filelog.json >>/var/log/node-problem-detector.log 2>&1"
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
