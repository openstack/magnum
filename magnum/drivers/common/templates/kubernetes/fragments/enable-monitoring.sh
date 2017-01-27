#!/bin/bash

. /etc/sysconfig/heat-params

if [ "$(echo $PROMETHEUS_MONITORING | tr '[:upper:]' '[:lower:]')" = "false" ]; then
    exit 0
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

KUBE_MON_BIN=/usr/local/bin/kube-enable-monitoring
KUBE_MON_SERVICE=/etc/systemd/system/kube-enable-monitoring.service
GRAFANA_DEF_DASHBOARDS="/var/lib/grafana/dashboards"
GRAFANA_DEF_DASHBOARD_FILE=$GRAFANA_DEF_DASHBOARDS"/default.json"

# Write the binary for enable-monitoring
KUBE_MON_BIN_CONTENT='''#!/bin/sh
until curl -sf "http://127.0.0.1:8080/healthz"
do
    echo "Waiting for Kubernetes API..."
    sleep 5
done

# Check if all resources exist already before creating them
# Check if configmap Prometheus exists
kubectl get configmap prometheus -n kube-system
if [ "$?" != "0" ] && \
        [ -f "/srv/kubernetes/monitoring/prometheusConfigMap.yaml" ]; then
    kubectl create -f /srv/kubernetes/monitoring/prometheusConfigMap.yaml
fi

# Check if deployment and service Prometheus exist
kubectl get service prometheus -n kube-system | kubectl get deployment prometheus -n kube-system
if [ "${PIPESTATUS[0]}" != "0" ] && [ "${PIPESTATUS[1]}" != "0" ] && \
        [ -f "/srv/kubernetes/monitoring/prometheusService.yaml" ]; then
    kubectl create -f /srv/kubernetes/monitoring/prometheusService.yaml
fi

# Check if configmap graf-dash exists
kubectl get configmap graf-dash -n kube-system
if [ "$?" != "0" ] && \
        [ -f '''$GRAFANA_DEF_DASHBOARD_FILE''' ]; then
    kubectl create configmap graf-dash --from-file='''$GRAFANA_DEF_DASHBOARD_FILE''' -n kube-system
fi

# Check if deployment and service Grafana exist
kubectl get service grafana -n kube-system | kubectl get deployment grafana -n kube-system
if [ "${PIPESTATUS[0]}" != "0" ] && [ "${PIPESTATUS[1]}" != "0" ] && \
        [ -f "/srv/kubernetes/monitoring/grafanaService.yaml" ]; then
    kubectl create -f /srv/kubernetes/monitoring/grafanaService.yaml
fi

# Wait for Grafana pod and then inject data source
while true
do
    echo "Waiting for Grafana pod to be up and Running"
    if [ "$(kubectl get po -n kube-system -l name=grafana -o jsonpath={..phase})" = "Running" ]; then
        break
    fi
    sleep 2
done

# Which node is running Grafana
NODE_IP=`kubectl get po -n kube-system -o jsonpath={.items[0].status.hostIP} -l name=grafana`
PROM_SERVICE_IP=`kubectl get svc prometheus --namespace kube-system -o jsonpath={..clusterIP}`

# The Grafana pod might be running but the app might still be initiating
echo "Check if Grafana is ready..."
curl --user admin:$ADMIN_PASSWD -X GET http://$NODE_IP:3000/api/datasources/1
until [ $? -eq 0 ]
do
    sleep 2
    curl --user admin:$ADMIN_PASSWD -X GET http://$NODE_IP:3000/api/datasources/1
done

# Inject Prometheus datasource into Grafana
while true
do
    INJECT=`curl --user admin:$ADMIN_PASSWD -X POST  \
        -H "Content-Type: application/json;charset=UTF-8" \
        --data-binary '''"'"'''{"name":"k8sPrometheus","isDefault":true,
            "type":"prometheus","url":"http://'''"'"'''$PROM_SERVICE_IP'''"'"''':9090","access":"proxy"}'''"'"'''\
        "http://$NODE_IP:3000/api/datasources/"`

    if [[ "$INJECT" = *"Datasource added"* ]]; then
        echo "Prometheus datasource injected into Grafana"
        break
    fi
    echo "Trying to inject Prometheus datasource into Grafana - "$INJECT
done
'''
writeFile $KUBE_MON_BIN "$KUBE_MON_BIN_CONTENT"


# Write the monitoring service
KUBE_MON_SERVICE_CONTENT='''[Unit]
Requires=kubelet.service

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
systemctl enable kube-enable-monitoring
systemctl start --no-block kube-enable-monitoring
