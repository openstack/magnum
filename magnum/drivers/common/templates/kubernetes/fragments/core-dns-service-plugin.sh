#!/bin/sh

step="core-dns-service-plugin"
printf "Starting to run ${step}\n"

. /etc/sysconfig/heat-params

_dns_prefix=${CONTAINER_INFRA_PREFIX:-registry.k8s.io/coredns/}
_autoscaler_prefix=${CONTAINER_INFRA_PREFIX:-gcr.io/google_containers/}
ssh_cmd="ssh -F /srv/magnum/.ssh/config root@localhost"

CORE_DNS_VALUES_YAML=/srv/magnum/kubernetes/helm/coredns/values.yaml
    echo "Writing File: $CORE_DNS_VALUES_YAML"
    mkdir -p $(dirname ${CORE_DNS_VALUES_YAML})
    cat << EOF > ${CORE_DNS_VALUES_YAML}
image:
  repository: ${_dns_prefix}coredns
  tag: "${COREDNS_TAG}"

replicaCount: 2

resources:
  limits:
    cpu: 100m
    memory: 128Mi
  requests:
    cpu: 100m
    memory: 128Mi

# isClusterService specifies whether chart should be deployed as cluster-service or normal k8s app.
isClusterService: true

# Optional priority class to be used for the coredns pods. Used for autoscaler if autoscaler.priorityClassName not set.
priorityClassName: "system-cluster-critical"

## Create HorizontalPodAutoscaler object.
autoscaling:
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      targetAverageUtilization: 60
  - type: Resource
    resource:
      name: memory
      targetAverageUtilization: 60

rollingUpdate:
  maxUnavailable: 1
  maxSurge: 25%

prometheus:
  service:
    enabled: true
    annotations:
      prometheus.io/scrape: "true"
      prometheus.io/port: "9153"
  monitor:
    enabled: false
    additionalLabels: {}
    namespace: ""

service:
  clusterIP: "${DNS_SERVICE_IP}"
  name: "kube-dns"

nodeSelector:
  kubernetes.io/os: linux

# Configure SecurityContext for Pod.
# Ensure that required linux capability to bind port number below 1024 is assigned (CAP_NET_BIND_SERVICE).
securityContext:
  capabilities:
    add:
      - NET_BIND_SERVICE

# expects input structure as per specification https://kubernetes.io/docs/reference/generated/kubernetes-api/v1.11/#toleration-v1-core
tolerations:
  # Make sure the pod can be scheduled on master kubelet.
  - effect: NoSchedule
    operator: Exists
  # Mark the pod as a critical add-on for rescheduling.
  - key: CriticalAddonsOnly
    operator: Exists
  - effect: NoExecute
    operator: Exists

# Default zone is what Kubernetes recommends:
# https://kubernetes.io/docs/tasks/administer-cluster/dns-custom-nameservers/#coredns-configmap-options
servers:
- zones:
  - zone: .
  port: 53
  plugins:
  - name: errors
  - name: log
  - name: autopath
    parameters: "@kubernetes"
  # Serves a /health endpoint on :8080, required for livenessProbe
  - name: health
    configBlock: |-
      lameduck 5s
  # Serves a /ready endpoint on :8181, required for readinessProbe
  - name: ready
  # Required to query kubernetes API for data
  #    parameters: ${DNS_CLUSTER_DOMAIN} in-addr.arpa ${PORTAL_NETWORK_CIDR} ${PODS_NETWORK_CIDR}
  - name: kubernetes
    parameters: ${DNS_CLUSTER_DOMAIN} in-addr.arpa ${PORTAL_NETWORK_CIDR} ${PODS_NETWORK_CIDR}
    configBlock: |-
      pods verified
      fallthrough in-addr.arpa
      ttl 30
  # Serves a /metrics endpoint on :9153, required for serviceMonitor
  - name: prometheus
    parameters: 0.0.0.0:9153
  - name: forward
    parameters: . 1.1.1.1 1.0.0.1 /etc/resolv.conf
  - name: cache
    parameters: 30
  - name: loop
  - name: reload
  - name: loadbalance

  image:
    repository: ${_autoscaler_prefix}cluster-proportional-autoscaler-${ARCH}
    tag: "1.8.5"

deployment:
  enabled: true
  name: "coredns"
EOF

echo "Waiting for Kubernetes API..."
until  [ "ok" = "$(kubectl get --raw='/healthz' 2>nil)" ]
do
    sleep 5
done

$ssh_cmd helm repo add coredns https://coredns.github.io/helm

if $ssh_cmd helm plugin list | grep -q "mapkubeapis"; then
    echo "mapkubeapis is already installed."
else
    echo "mapkubeapis is not installed. Installing now..."
    $ssh_cmd helm plugin install https://github.com/helm/helm-mapkubeapis
fi

if $ssh_cmd helm list --namespace kube-system | grep -q "coredns"; then
    $ssh_cmd helm mapkubeapis coredns --namespace kube-system
fi

$ssh_cmd helm upgrade -i coredns coredns/coredns --version 1.22.0 -n kube-system -f ${CORE_DNS_VALUES_YAML} --wait

if $ssh_cmd helm list --namespace kube-system | grep -q "coredns"; then
    $ssh_cmd helm mapkubeapis coredns --namespace kube-system
fi

printf "Finished running ${step}\n"
