
step="enable-auto-healing-plugin"
printf "Starting to run ${step}\n"

. /etc/sysconfig/heat-params

auto_healing_plugin_enabled=$(echo $AUTO_HEALING_ENABLED | tr '[:upper:]' '[:lower:]')
ssh_cmd="ssh -F /srv/magnum/.ssh/config root@localhost"

if [[ "${auto_healing_plugin_enabled}" = "true" ]]; then

_k8s_prefix=${CONTAINER_INFRA_PREFIX:-registry.k8s.io/}

CLUSTER_NPD_VALUES_YAML=/srv/magnum/kubernetes/helm/cluster-npd/values.yaml
    echo "Writing File: $CLUSTER_NPD_VALUES_YAML"
    mkdir -p $(dirname ${CLUSTER_NPD_VALUES_YAML})
    cat << EOF > ${CLUSTER_NPD_VALUES_YAML}
settings:
  custom_monitor_definitions: {}
  log_monitors:
    - /config/kernel-monitor.json
    - /config/docker-monitor.json
  custom_plugin_monitors: []
  extraArgs: []

  # settings.prometheus_address -- Prometheus exporter address
  prometheus_address: 0.0.0.0
  # settings.prometheus_port -- Prometheus exporter port
  prometheus_port: 20257

  # The period at which k8s-exporter does forcibly sync with apiserver
  # settings.heartBeatPeriod -- Syncing interval with API server
  heartBeatPeriod: 5m0s

logDir:
  # logDir.host -- log directory on k8s host
  host: /var/log/
  # logDir.pod -- log directory in pod (volume mount), use logDir.host if empty
  pod: ""

image:
  repository: ${_k8s_prefix}node-problem-detector/node-problem-detector
  # image.digest -- the image digest. If given it takes precedence over a given tag.
  digest: ""
  pullPolicy: IfNotPresent

imagePullSecrets: []

nameOverride: ""
fullnameOverride: "node-problem-detector"

rbac:
  create: true
  pspEnabled: false

hostNetwork: false
hostPID: false

priorityClassName: system-node-critical

securityContext:
  privileged: true

resources: {}

annotations: {}

labels: {}

tolerations:
  - effect: NoSchedule
    operator: Exists

serviceAccount:
  # Specifies whether a ServiceAccount should be created
  create: true
  # The name of the ServiceAccount to use.
  # If not set and create is true, a name is generated using the fullname template
  name:

affinity: {}

nodeSelector: {}

metrics:
  # metrics.enabled -- Expose metrics in Prometheus format with default configuration.
  enabled: false
  # metrics.annotations -- Override all default annotations when metrics.enabled=true with specified values.
  annotations: {}
  serviceMonitor:
    enabled: false
    additionalLabels: {}
  prometheusRule:
    enabled: false
    defaultRules:
      create: true
      disabled: []
    additionalLabels: {}
    additionalRules: []

env:
#  - name: FOO
#    value: BAR
#  - name: POD_NAME
#    valueFrom:
#      fieldRef:
#        fieldPath: metadata.name

extraVolumes: []

extraVolumeMounts: []

extraContainers: []

# updateStrategy -- Manage the daemonset update strategy
updateStrategy: RollingUpdate
# maxUnavailable -- The max pods unavailable during an update
maxUnavailable: 1
EOF

    MAGNUM_AUTOHEALER_YAML=/srv/magnum/kubernetes/magnum-autohealer.yaml
    echo "Writing File: $MAGNUM_AUTOHEALER_YAML"
    mkdir -p $(dirname ${MAGNUM_AUTOHEALER_YAML})
cat << EOF > ${MAGNUM_AUTOHEALER_YAML}
---
kind: ServiceAccount
apiVersion: v1
metadata:
  name: magnum-auto-healer
  namespace: kube-system

---
kind: ClusterRoleBinding
apiVersion: rbac.authorization.k8s.io/v1
metadata:
  name: magnum-auto-healer
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: cluster-admin
subjects:
  - kind: ServiceAccount
    name: magnum-auto-healer
    namespace: kube-system

---
kind: ConfigMap
apiVersion: v1
metadata:
  name: magnum-auto-healer-config
  namespace: kube-system
data:
  config.yaml: |
    cluster-name: ${CLUSTER_UUID}
    dry-run: false
    monitor-interval: 15s
    check-delay-after-add: 20m
    leader-elect: true
    healthcheck:
      master:
        - type: Endpoint
          params:
            unhealthy-duration: 30s
            protocol: HTTPS
            port: 6443
            endpoints: ["/healthz"]
            ok-codes: [200]
        - type: NodeCondition
          params:
            unhealthy-duration: 1m
            types: ["Ready"]
            ok-values: ["True"]
      worker:
        - type: NodeCondition
          params:
            unhealthy-duration: 1m
            types: ["Ready"]
            ok-values: ["True"]
    openstack:
      auth-url: ${AUTH_URL}
      user-id: ${TRUSTEE_USER_ID}
      password: ${TRUSTEE_PASSWORD}
      trust-id: ${TRUST_ID}
      region: ${REGION_NAME}
      ca-file: /etc/kubernetes/ca-bundle.crt
---
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: magnum-auto-healer
  namespace: kube-system
  labels:
    k8s-app: magnum-auto-healer
spec:
  selector:
    matchLabels:
      k8s-app: magnum-auto-healer
  template:
    metadata:
      labels:
        k8s-app: magnum-auto-healer
    spec:
      serviceAccountName: magnum-auto-healer
      tolerations:
        - effect: NoSchedule
          operator: Exists
        - key: CriticalAddonsOnly
          operator: Exists
        - effect: NoExecute
          operator: Exists
      dnsPolicy: Default
      nodeSelector:
        node-role.kubernetes.io/${LEAD_NODE_ROLE_NAME}: ""
      containers:
        - name: magnum-auto-healer
          image: ${_k8s_prefix}provider-os/magnum-auto-healer:v1.27.1
          imagePullPolicy: Always
          args:
            - /bin/magnum-auto-healer
            - --config=/etc/magnum-auto-healer/config.yaml
            - --v
            - "2"
          volumeMounts:
            - name: config
              mountPath: /etc/magnum-auto-healer
            - name: kubernetes-config
              mountPath: /etc/kubernetes
              readOnly: true
      volumes:
        - name: config
          configMap:
            name: magnum-auto-healer-config
        - name: kubernetes-config
          hostPath:
            path: /etc/kubernetes
EOF

$ssh_cmd kubectl apply -f ${MAGNUM_AUTOHEALER_YAML}

$ssh_cmd helm repo add deliveryhero https://charts.deliveryhero.io/

if $ssh_cmd helm plugin list | grep -q "mapkubeapis"; then
    echo "mapkubeapis is already installed."
else
    echo "mapkubeapis is not installed. Installing now..."
    $ssh_cmd helm plugin install https://github.com/helm/helm-mapkubeapis
fi

if $ssh_cmd helm list --namespace kube-system | grep -q "npd"; then
    $ssh_cmd helm mapkubeapis npd --namespace kube-system
fi
$ssh_cmd helm repo update
$ssh_cmd helm upgrade -i npd deliveryhero/node-problem-detector --version 2.3.4 -n kube-system -f ${CLUSTER_NPD_VALUES_YAML}

if $ssh_cmd helm list --namespace kube-system | grep -q "npd"; then
    $ssh_cmd helm mapkubeapis npd --namespace kube-system
fi

fi
printf "Finished running ${step}\n"