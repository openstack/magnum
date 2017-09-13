#!/bin/sh

. /etc/sysconfig/heat-params

if [ "$(echo $PROMETHEUS_MONITORING | tr '[:upper:]' '[:lower:]')" = "false" ]; then
    exit 0
fi

# Write node-exporter manifest as a regular pod
node_exporter_file=/etc/kubernetes/manifests/node-exporter.yaml
[ -f ${node_exporter_file} ] || {
    echo "Writing File: $node_exporter_file"
    mkdir -p $(dirname ${node_exporter_file})
    cat << EOF > ${node_exporter_file}
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
}
