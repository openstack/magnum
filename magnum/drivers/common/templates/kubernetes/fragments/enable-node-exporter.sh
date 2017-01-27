#!/bin/sh

. /etc/sysconfig/heat-params

if [ "$(echo $PROMETHEUS_MONITORING | tr '[:upper:]' '[:lower:]')" = "false" ]; then
    exit 0
fi

# Write node-exporter manifest as a regular pod
cat > /etc/kubernetes/manifests/node-exporter.yaml << EOF
apiVersion: v1
kind: Pod
metadata:
  name: node-exporter
  namespace: kube-system
  annotations:
    prometheus.io/scrape: "true"
  labels:
    app: node-exporter
spec:
  containers:
  - name: node-exporter
    image: prom/node-exporter
    ports:
    - containerPort: 9100
      hostPort: 9100
EOF
