step="enable-prometheus-monitoring"
printf "Starting to run ${step}\n"

. /etc/sysconfig/heat-params

if [ ! -z "$HTTP_PROXY" ]; then
    export HTTP_PROXY
fi

if [ ! -z "$HTTPS_PROXY" ]; then
    export HTTPS_PROXY
fi

if [ ! -z "$NO_PROXY" ]; then
    export NO_PROXY
fi

function writeFile {
    # $1 is filename
    # $2 is file content

    [ -f ${1} ] || {
        echo "Writing File: $1"
        mkdir -p $(dirname ${1})
        cat << EOF > ${1}
$2
EOF
    }
}

prometheusConfigMap_file=/srv/magnum/kubernetes/monitoring/prometheusConfigMap.yaml
[ -f ${prometheusConfigMap_file} ] || {
    echo "Writing File: $prometheusConfigMap_file"
    mkdir -p $(dirname ${prometheusConfigMap_file})
    # NOTE: EOF needs to be in quotes in order to not escape the $ characters
    cat << 'EOF' > ${prometheusConfigMap_file}
apiVersion: v1
kind: ConfigMap
metadata:
  name: prometheus
  namespace: prometheus-monitoring
data:
  prometheus.yml: |
    global:
      scrape_interval: 10s
      scrape_timeout: 10s
      evaluation_interval: 10s

    scrape_configs:
    - job_name: 'kubernetes-apiservers'

      kubernetes_sd_configs:
      - role: endpoints

      scheme: https

      tls_config:
        ca_file: /var/run/secrets/kubernetes.io/serviceaccount/ca.crt
      bearer_token_file: /var/run/secrets/kubernetes.io/serviceaccount/token
      relabel_configs:
      - source_labels: [__meta_kubernetes_namespace, __meta_kubernetes_service_name, __meta_kubernetes_endpoint_port_name]
        action: keep
        regex: default;kubernetes;https
    - job_name: 'kubernetes-nodes'
      scheme: https
      tls_config:
        ca_file: /var/run/secrets/kubernetes.io/serviceaccount/ca.crt
      bearer_token_file: /var/run/secrets/kubernetes.io/serviceaccount/token
      kubernetes_sd_configs:
      - role: node
      relabel_configs:
      - action: labelmap
        regex: __meta_kubernetes_node_label_(.+)
      - target_label: __address__
        replacement: kubernetes.default.svc:443
      - source_labels: [__meta_kubernetes_node_name]
        regex: (.+)
        target_label: __metrics_path__
        replacement: /api/v1/nodes/${1}/proxy/metrics

    - job_name: 'kubernetes-cadvisor'
      scheme: https
      tls_config:
        ca_file: /var/run/secrets/kubernetes.io/serviceaccount/ca.crt
      bearer_token_file: /var/run/secrets/kubernetes.io/serviceaccount/token
      kubernetes_sd_configs:
      - role: node
      relabel_configs:
      - action: labelmap
        regex: __meta_kubernetes_node_label_(.+)
      - target_label: __address__
        replacement: kubernetes.default.svc:443
      - source_labels: [__meta_kubernetes_node_name]
        regex: (.+)
        target_label: __metrics_path__
        replacement: /api/v1/nodes/${1}/proxy/metrics/cadvisor

    - job_name: 'kubernetes-service-endpoints'

      kubernetes_sd_configs:
      - role: endpoints

      relabel_configs:
      - source_labels: [__meta_kubernetes_service_annotation_prometheus_io_scrape]
        action: keep
        regex: true
      - source_labels: [__meta_kubernetes_service_annotation_prometheus_io_scheme]
        action: replace
        target_label: __scheme__
        regex: (https?)
      - source_labels: [__meta_kubernetes_service_annotation_prometheus_io_path]
        action: replace
        target_label: __metrics_path__
        regex: (.+)
      - source_labels: [__address__, __meta_kubernetes_service_annotation_prometheus_io_port]
        action: replace
        target_label: __address__
        regex: ([^:]+)(?::\d+)?;(\d+)
        replacement: $1:$2
      - action: labelmap
        regex: __meta_kubernetes_service_label_(.+)
      - source_labels: [__meta_kubernetes_namespace]
        action: replace
        target_label: kubernetes_namespace
      - source_labels: [__meta_kubernetes_service_name]
        action: replace
        target_label: kubernetes_name

    - job_name: 'kubernetes-services'
      metrics_path: /probe
      params:
        module: [http_2xx]
      kubernetes_sd_configs:
      - role: service
      relabel_configs:
      - source_labels: [__meta_kubernetes_service_annotation_prometheus_io_probe]
        action: keep
        regex: true
      - source_labels: [__address__]
        target_label: __param_target
      - target_label: __address__
        replacement: blackbox
      - source_labels: [__param_target]
        target_label: instance
      - action: labelmap
        regex: __meta_kubernetes_service_label_(.+)
      - source_labels: [__meta_kubernetes_namespace]
        target_label: kubernetes_namespace
      - source_labels: [__meta_kubernetes_service_name]
        target_label: kubernetes_name

    - job_name: 'kubernetes-pods'
      kubernetes_sd_configs:
      - role: pod
      relabel_configs:
      - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_scrape]
        action: keep
        regex: true
      - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_path]
        action: replace
        target_label: __metrics_path__
        regex: (.+)
      - source_labels: [__address__, __meta_kubernetes_pod_annotation_prometheus_io_port]
        action: replace
        regex: ([^:]+)(?::\d+)?;(\d+)
        replacement: $1:$2
        target_label: __address__
      - action: labelmap
        regex: __meta_kubernetes_pod_label_(.+)
      - source_labels: [__meta_kubernetes_namespace]
        action: replace
        target_label: kubernetes_namespace
      - source_labels: [__meta_kubernetes_pod_name]
        action: replace
        target_label: kubernetes_pod_name

    - job_name: 'kubernetes-node-exporter'
      tls_config:
        ca_file: /var/run/secrets/kubernetes.io/serviceaccount/ca.crt
      bearer_token_file: /var/run/secrets/kubernetes.io/serviceaccount/token
      kubernetes_sd_configs:
      - role: node
      relabel_configs:
      - action: labelmap
        regex: __meta_kubernetes_node_label_(.+)
      - source_labels: [__meta_kubernetes_role]
        action: replace
        target_label: kubernetes_role
      - source_labels: [__address__]
        regex: '(.*):10250'
        replacement: '${1}:9100'
        target_label: __address__
EOF
}

prometheusService_file=/srv/magnum/kubernetes/monitoring/prometheusService.yaml
prometheusService_content=$(cat <<EOF
apiVersion: v1
kind: Service
metadata:
  annotations:
    prometheus.io/scrape: 'true'
  labels:
    name: prometheus
  name: prometheus
  namespace: prometheus-monitoring
spec:
  selector:
    app: prometheus
  type: ClusterIP
  ports:
  - name: prometheus
    protocol: TCP
    port: 9090
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: prometheus
  namespace: prometheus-monitoring
spec:
  replicas: 1
  selector:
    matchLabels:
      app: prometheus
  template:
    metadata:
      name: prometheus
      labels:
        app: prometheus
    spec:
      serviceAccountName: prometheus
      containers:
      - name: prometheus
        image: ${CONTAINER_INFRA_PREFIX:-docker.io/prom/}prometheus:${PROMETHEUS_TAG}
        args:
          - '-storage.local.retention=6h'
          - '-storage.local.memory-chunks=500000'
          - '-config.file=/etc/prometheus/prometheus.yml'
        ports:
        - name: web
          containerPort: 9090
          hostPort: 9090
        volumeMounts:
        - name: config-volume
          mountPath: /etc/prometheus
      volumes:
      - name: config-volume
        configMap:
          name: prometheus
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: prometheus
rules:
- apiGroups: [""]
  resources:
  - nodes
  - nodes/proxy
  - services
  - endpoints
  - pods
  verbs: ["get", "list", "watch"]
- apiGroups:
  - extensions
  resources:
  - ingresses
  verbs: ["get", "list", "watch"]
- nonResourceURLs: ["/metrics"]
  verbs: ["get"]
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: prometheus
  namespace: prometheus-monitoring
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: prometheus
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: prometheus
subjects:
- kind: ServiceAccount
  name: prometheus
  namespace: prometheus-monitoring
EOF
)
writeFile $prometheusService_file "$prometheusService_content"

# Write the file for prometheus-monitoring namespace
prometheusNamespace_file=/srv/magnum/kubernetes/monitoring/prometheusNamespace.yaml
prometheusNamespace_content=$(cat <<EOF
apiVersion: v1
kind: Namespace
metadata:
  labels:
    name: prometheus-monitoring
  name: prometheus-monitoring
EOF
)
writeFile $prometheusNamespace_file "$prometheusNamespace_content"

grafanaService_file=/srv/magnum/kubernetes/monitoring/grafanaService.yaml
grafanaService_content=$(cat <<EOF
apiVersion: v1
kind: Service
metadata:
  labels:
    name: node
    role: service
  name: grafana
  namespace: prometheus-monitoring
spec:
  type: ClusterIP
  ports:
    - port: 3000
      targetPort: 3000
  selector:
    grafana: "true"
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: grafana
  namespace: prometheus-monitoring
spec:
  replicas: 1
  selector:
    matchLabels:
      name: grafana
      grafana: "true"
      role: db
  template:
    metadata:
      labels:
        name: grafana
        grafana: "true"
        role: db
    spec:
      containers:
        - image: ${CONTAINER_INFRA_PREFIX:-docker.io/grafana/}grafana:${GRAFANA_TAG}
          imagePullPolicy: IfNotPresent
          name: grafana
          env:
            - name: GF_SECURITY_ADMIN_PASSWORD
              value: ${GRAFANA_ADMIN_PASSWD}
            - name: GF_DASHBOARDS_JSON_ENABLED
              value: "true"
            - name: GF_DASHBOARDS_JSON_PATH
              value: /var/lib/grafana/dashboards
          resources:
            # keep request = limit to keep this container in guaranteed class
            limits:
              cpu: 100m
              memory: 200Mi
            requests:
              cpu: 100m
              memory: 200Mi
          volumeMounts:
          - name: default-dashboard
            mountPath: /var/lib/grafana/dashboards
          ports:
            - containerPort: 3000
              hostPort: 3000
      volumes:
      - name: default-dashboard
        configMap:
          name: graf-dash
EOF
)
writeFile $grafanaService_file "$grafanaService_content"

nodeExporter_file=/srv/magnum/kubernetes/monitoring/nodeExporter.yaml
nodeExporter_content=$(cat <<EOF
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: node-exporter
  namespace: prometheus-monitoring
  labels:
    k8s-app: node-exporter
    kubernetes.io/cluster-service: "true"
    addonmanager.kubernetes.io/mode: Reconcile
    version: v0.15.2
spec:
  selector:
    matchLabels:
      k8s-app: node-exporter
      version: v0.15.2
  updateStrategy:
    type: OnDelete
  template:
    metadata:
      labels:
        k8s-app: node-exporter
        version: v0.15.2
      annotations:
        scheduler.alpha.kubernetes.io/critical-pod: ''
    spec:
      tolerations:
        # Make sure calico/node gets scheduled on all nodes.
        - effect: NoSchedule
          operator: Exists
        # Mark the pod as a critical add-on for rescheduling.
        - key: CriticalAddonsOnly
          operator: Exists
        - effect: NoExecute
          operator: Exists
      priorityClassName: system-node-critical
      containers:
        - name: prometheus-node-exporter
          image: "${CONTAINER_INFRA_PREFIX:-docker.io/prom/}node-exporter:v0.15.2"
          imagePullPolicy: "IfNotPresent"
          args:
            - --path.procfs=/host/proc
            - --path.sysfs=/host/sys
          ports:
            - name: metrics
              containerPort: 9100
              hostPort: 9100
          volumeMounts:
            - name: proc
              mountPath: /host/proc
              readOnly:  true
            - name: sys
              mountPath: /host/sys
              readOnly: true
          resources:
            limits:
              cpu: 10m
              memory: 50Mi
            requests:
              cpu: 10m
              memory: 50Mi
      hostNetwork: true
      hostPID: true
      volumes:
        - name: proc
          hostPath:
            path: /proc
        - name: sys
          hostPath:
            path: /sys
EOF
)
writeFile $nodeExporter_file "$nodeExporter_content"

. /etc/sysconfig/heat-params


if [ "$(echo $PROMETHEUS_MONITORING | tr '[:upper:]' '[:lower:]')" = "true" ]; then
    PROMETHEUS_MON_BASE_DIR="/srv/magnum/kubernetes/monitoring"
    KUBE_MON_BIN=${PROMETHEUS_MON_BASE_DIR}"/bin/kube-enable-monitoring"
    KUBE_MON_SERVICE="/etc/systemd/system/kube-enable-monitoring.service"
    GRAFANA_DEF_DASHBOARDS=${PROMETHEUS_MON_BASE_DIR}"/dashboards"
    GRAFANA_DEF_DASHBOARD_FILE=$GRAFANA_DEF_DASHBOARDS"/default.json"

    # Write the binary for enable-monitoring
    KUBE_MON_BIN_CONTENT='''#!/bin/sh
until  [ "ok" = "$(kubectl get --raw='/healthz')" ]
do
    echo "Waiting for Kubernetes API..."
    sleep 5
done

# Check if prometheus-monitoring namespace exist already before creating the namespace
kubectl get namespace prometheus-monitoring
if [ "$?" != "0" ] && \
        [ -f "'''${PROMETHEUS_MON_BASE_DIR}'''/prometheusNamespace.yaml" ]; then
    kubectl apply -f  '''${PROMETHEUS_MON_BASE_DIR}'''/prometheusNamespace.yaml
fi

# Check if all resources exist already before creating them
# Check if configmap Prometheus exists
kubectl get configmap prometheus -n prometheus-monitoring
if [ "$?" != "0" ] && \
        [ -f "'''${PROMETHEUS_MON_BASE_DIR}'''/prometheusConfigMap.yaml" ]; then
    kubectl apply -f '''${PROMETHEUS_MON_BASE_DIR}'''/prometheusConfigMap.yaml
fi

# Check if deployment and service Prometheus exist
kubectl get service prometheus -n prometheus-monitoring | kubectl get deployment prometheus -n prometheus-monitoring
if [ "${PIPESTATUS[0]}" != "0" ] && [ "${PIPESTATUS[1]}" != "0" ] && \
        [ -f "'''${PROMETHEUS_MON_BASE_DIR}'''/prometheusService.yaml" ]; then
    kubectl apply -f '''${PROMETHEUS_MON_BASE_DIR}'''/prometheusService.yaml
fi

# Check if node exporter daemonset exist
kubectl get daemonset node-exporter -n prometheus-monitoring
if [ "$?" != "0" ] && \
        [ -f "'''${PROMETHEUS_MON_BASE_DIR}'''/nodeExporter.yaml" ]; then
    kubectl apply -f '''${PROMETHEUS_MON_BASE_DIR}'''/nodeExporter.yaml
fi

# Check if configmap graf-dash exists
kubectl get configmap graf-dash -n prometheus-monitoring
if [ "$?" != "0" ] && \
        [ -f '''$GRAFANA_DEF_DASHBOARD_FILE''' ]; then
    kubectl create configmap graf-dash --from-file='''$GRAFANA_DEF_DASHBOARD_FILE''' -n prometheus-monitoring
fi

# Check if deployment and service Grafana exist
kubectl get service grafana -n prometheus-monitoring | kubectl get deployment grafana -n prometheus-monitoring
if [ "${PIPESTATUS[0]}" != "0" ] && [ "${PIPESTATUS[1]}" != "0" ] && \
        [ -f "'''${PROMETHEUS_MON_BASE_DIR}'''/grafanaService.yaml" ]; then
    kubectl apply -f '''${PROMETHEUS_MON_BASE_DIR}'''/grafanaService.yaml
fi

# Wait for Grafana pod and then inject data source
while true
do
    echo "Waiting for Grafana pod to be up and Running"
    if [ "$(kubectl get po -n prometheus-monitoring -l name=grafana -o jsonpath={..phase})" = "Running" ]; then
        break
    fi
    sleep 2
done

# Which node is running Grafana
NODE_IP=`kubectl get po -n prometheus-monitoring -o jsonpath={.items[0].status.hostIP} -l name=grafana`
PROM_SERVICE_IP=`kubectl get svc prometheus --namespace prometheus-monitoring -o jsonpath={..clusterIP}`
GRAFANA_SERVICE_IP=`kubectl get svc grafana --namespace prometheus-monitoring -o jsonpath={..clusterIP}`

# The Grafana pod might be running but the app might still be initiating
echo "Check if Grafana is ready..."
curl -sS --user admin:$ADMIN_PASSWD -X GET http://$GRAFANA_SERVICE_IP:3000/api/datasources/1
until [ $? -eq 0 ]
do
    sleep 2
    curl -sS --user admin:$ADMIN_PASSWD -X GET http://$GRAFANA_SERVICE_IP:3000/api/datasources/1
done

# Inject Prometheus datasource into Grafana
while true
do
    INJECT=`curl -sS --user admin:$ADMIN_PASSWD -X POST  \
        -H "Content-Type: application/json;charset=UTF-8" \
        --data-binary '''"'"'''{"name":"k8sPrometheus","isDefault":true,
            "type":"prometheus","url":"http://'''"'"'''$PROM_SERVICE_IP'''"'"''':9090","access":"proxy"}'''"'"'''\
        "http://$GRAFANA_SERVICE_IP:3000/api/datasources/"`

    if [[ "$INJECT" = *"Datasource added"* ]]; then
        echo "Prometheus datasource injected into Grafana"
        break
    elif [[ "$INJECT" = *"Data source with same name already exists"* ]]; then
        echo "Prometheus datasource already injected into Grafana"
        break
    fi

    echo "Trying to inject Prometheus datasource into Grafana - "$INJECT
done
'''
    writeFile $KUBE_MON_BIN "$KUBE_MON_BIN_CONTENT"


    # Write the monitoring service
    KUBE_MON_SERVICE_CONTENT='''[Unit]
Description=Enable Prometheus monitoring stack

[Service]
Type=oneshot
Environment=HOME=/root
EnvironmentFile=-/etc/kubernetes/config
ExecStart='''${KUBE_MON_BIN}'''

[Install]
WantedBy=multi-user.target
'''
    writeFile $KUBE_MON_SERVICE "$KUBE_MON_SERVICE_CONTENT"

    chown root:root ${KUBE_MON_BIN}
    chmod 0755 ${KUBE_MON_BIN}

    chown root:root ${KUBE_MON_SERVICE}
    chmod 0644 ${KUBE_MON_SERVICE}

    # Download the default JSON Grafana dashboard
    # Not a crucial step, so allow it to fail
    # TODO: this JSON should be passed into the minions as gzip in cloud-init
    GRAFANA_DASHB_URL="https://grafana.net/api/dashboards/1621/revisions/1/download"
    mkdir -p $GRAFANA_DEF_DASHBOARDS
    curl $GRAFANA_DASHB_URL -o $GRAFANA_DEF_DASHBOARD_FILE || echo "Failed to fetch default Grafana dashboard"
    if [ -f $GRAFANA_DEF_DASHBOARD_FILE ]; then
        sed -i -- 's|${DS_PROMETHEUS}|k8sPrometheus|g' $GRAFANA_DEF_DASHBOARD_FILE
    fi

    # Launch the monitoring service
    set -x
    systemctl daemon-reload
    systemctl enable kube-enable-monitoring.service
    systemctl start --no-block kube-enable-monitoring.service
fi

printf "Finished running ${step}\n"
