#!/bin/bash

. /etc/sysconfig/heat-params

set -ex

step="prometheus-operator"
printf "Starting to run ${step}\n"

### Configuration
###############################################################################
CHART_NAME="prometheus-operator"

if [ "$(echo ${MONITORING_ENABLED} | tr '[:upper:]' '[:lower:]')" = "true" ]; then

    # Calculate resources needed to run the Prometheus Monitoring Solution
    # MAX_NODE_COUNT so we can have metrics even if cluster scales
    PROMETHEUS_SERVER_CPU=$(expr 128 + 7 \* ${MAX_NODE_COUNT} )
    PROMETHEUS_SERVER_RAM=$(expr 256 + 40 \* ${MAX_NODE_COUNT})

    # Validate if communication node <-> master is secure or insecure
    PROTOCOL="https"
    INSECURE_SKIP_VERIFY="False"
    if [ "$TLS_DISABLED" = "True" ]; then
        PROTOCOL="http"
        INSECURE_SKIP_VERIFY="True"
    fi

    if [ "$(echo ${VERIFY_CA} | tr '[:upper:]' '[:lower:]')" == "false" ]; then
        INSECURE_SKIP_VERIFY="True"
    fi

    HELM_MODULE_CONFIG_FILE="/srv/magnum/kubernetes/helm/${CHART_NAME}.yaml"
    [ -f ${HELM_MODULE_CONFIG_FILE} ] || {
        echo "Writing File: ${HELM_MODULE_CONFIG_FILE}"
        mkdir -p $(dirname ${HELM_MODULE_CONFIG_FILE})
        cat << EOF > ${HELM_MODULE_CONFIG_FILE}
---
kind: ConfigMap
apiVersion: v1
metadata:
  name: ${CHART_NAME}-config
  namespace: magnum-tiller
  labels:
    app: helm
data:
  install-${CHART_NAME}.sh: |
    #!/bin/bash
    set -ex
    mkdir -p \${HELM_HOME}
    cp /etc/helm/* \${HELM_HOME}

    # HACK - Force wait because of bug https://github.com/helm/helm/issues/5170
    until helm init --client-only --wait
    do
        sleep 5s
    done
    helm repo update

    if [[ \$(helm history ${CHART_NAME} | grep ${CHART_NAME}) ]]; then
        echo "${CHART_NAME} already installed on server. Continue..."
        exit 0
    else
        # TODO: Set namespace to monitoring. This is needed as the Kubernetes default priorityClass can only be used in NS kube-system
        helm install stable/${CHART_NAME} --namespace kube-system --name ${CHART_NAME} --version ${PROMETHEUS_OPERATOR_CHART_TAG} --values /opt/magnum/install-${CHART_NAME}-values.yaml
    fi

  install-${CHART_NAME}-values.yaml:  |
    nameOverride: prometheus
    fullnameOverride: prometheus

    alertmanager:
      alertmanagerSpec:
        image:
          repository: ${CONTAINER_INFRA_PREFIX:-quay.io/prometheus/}alertmanager
        # # Needs testing
        # resources:
        #   requests:
        #     cpu: 100m
        #     memory: 256Mi
        priorityClassName: "system-cluster-critical"


    # Dashboard
    grafana:
      #enabled: ${ENABLE_GRAFANA}
      resources:
        requests:
          cpu: 100m
          memory: 128Mi
      adminPassword: ${ADMIN_PASSWD}

    kubeApiServer:
      tlsConfig:
        insecureSkipVerify: ${INSECURE_SKIP_VERIFY}

    kubelet:
      serviceMonitor:
        https: ${PROTOCOL}

    coreDns:
      enabled: true
      service:
        port: 9153
        targetPort: 9153
        selector:
          k8s-app: kube-dns

    kubeEtcd:
      serviceMonitor:
        scheme: ${PROTOCOL}
        insecureSkipVerify: true
        ##  If Protocol is http this files should be neglected
        caFile: /etc/prometheus/secrets/etcd-certificates/ca.crt
        certFile: /etc/prometheus/secrets/etcd-certificates/kubelet.crt
        keyFile: /etc/prometheus/secrets/etcd-certificates/kubelet.key

    kube-state-metrics:
      priorityClassName: "system-cluster-critical"
      resources:
        #Guaranteed
        limits:
          cpu: 50m
          memory: 64M

    prometheus-node-exporter:
      priorityClassName: "system-node-critical"
      resources:
        #Guaranteed
        limits:
          cpu: 20m
          memory: 20M

    prometheusOperator:
      priorityClassName: "system-cluster-critical"
      image:
        repository: ${CONTAINER_INFRA_PREFIX:-quay.io/coreos/}prometheus-operator
      configmapReloadImage:
        repository: ${CONTAINER_INFRA_PREFIX:-quay.io/coreos/}configmap-reload
      prometheusConfigReloaderImage:
        repository: ${CONTAINER_INFRA_PREFIX:-quay.io/coreos/}prometheus-config-reloader
      hyperkubeImage:
        repository: ${CONTAINER_INFRA_PREFIX:-gcr.io/google-containers/}hyperkube

    prometheus:
      prometheusSpec:
        scrapeInterval: 30s
        evaluationInterval: 30s
        image:
          repository: ${CONTAINER_INFRA_PREFIX:-quay.io/prometheus/}prometheus
        retention: 14d
        resources:
          requests:
            cpu: ${PROMETHEUS_SERVER_CPU}m
            memory: ${PROMETHEUS_SERVER_RAM}M
        # secrets:
        # - etcd-certificates
        priorityClassName: "system-cluster-critical"

---
apiVersion: batch/v1
kind: Job
metadata:
  name: install-${CHART_NAME}-job
  namespace: magnum-tiller
spec:
  backoffLimit: 10
  template:
    spec:
      serviceAccountName: tiller
      containers:
      - name: config-helm
        image: ${CONTAINER_INFRA_PREFIX:-docker.io/openstackmagnum/}helm-client:${HELM_CLIENT_TAG}
        command:
        - bash
        args:
        - /opt/magnum/install-${CHART_NAME}.sh
        env:
        - name: HELM_HOME
          value: /helm_home
        - name: TILLER_NAMESPACE
          value: magnum-tiller
        - name: HELM_TLS_ENABLE
          value: "true"
        volumeMounts:
        - name: install-${CHART_NAME}-config
          mountPath: /opt/magnum/
        - mountPath: /etc/helm
          name: helm-client-certs
      restartPolicy: Never
      volumes:
      - name: install-${CHART_NAME}-config
        configMap:
          name: ${CHART_NAME}-config
      - name: helm-client-certs
        secret:
          secretName: helm-client-secret
EOF
    }

fi

printf "Finished running ${step}\n"
