#!/bin/bash

. /etc/sysconfig/heat-params

set -ex

step="prometheus-operator"
printf "Starting to run ${step}\n"

### Configuration
###############################################################################
CHART_NAME="prometheus-operator"
CHART_VERSION="0.1.31"

if [ "$(echo ${MONITORING_ENABLED} | tr '[:upper:]' '[:lower:]')" = "true" ]; then

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

    if [[ \$(helm history prometheus-operator | grep prometheus-operator) ]]; then
        echo "${CHART_NAME} already installed on server. Continue..."
        exit 0
    else
        helm install stable/${CHART_NAME} --namespace monitoring --name ${CHART_NAME} --version v${CHART_VERSION} --values /opt/magnum/install-${CHART_NAME}-values.yaml
    fi

  install-${CHART_NAME}-values.yaml:  |
    nameOverride: prometheus
    fullnameOverride: prometheus

    alertmanager:
      alertmanagerSpec:
        image:
          repository: ${CONTAINER_INFRA_PREFIX:-quay.io/}prometheus/alertmanager

    # Dashboard
    grafana:
      #enabled: ${ENABLE_GRAFANA}
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
          k8s-app: coredns

    kubeEtcd:
      service:
        port: 4001
        targetPort: 4001
        selector:
          k8s-app: etcd-server
      serviceMonitor:
        scheme: ${PROTOCOL}
        insecureSkipVerify: ${INSECURE_SKIP_VERIFY}
        ##  If Protocol is http this files should be neglected
        caFile: ${CERT_DIR}/ca.crt
        certFile: ${CERT_DIR}/kubelet.crt
        keyFile: ${CERT_DIR}/kubelet.key

    prometheusOperator:
      image:
        repository: ${CONTAINER_INFRA_PREFIX:-quay.io/}coreos/prometheus-operator
      configmapReloadImage:
        repository: ${CONTAINER_INFRA_PREFIX:-quay.io/}coreos/configmap-reload
      prometheusConfigReloaderImage:
        repository: ${CONTAINER_INFRA_PREFIX:-quay.io/}coreos/prometheus-config-reloader
      hyperkubeImage:
        repository: ${CONTAINER_INFRA_PREFIX:-gcr.io/google-containers/}hyperkube

    prometheus:
      prometheusSpec:
        image:
          repository: ${CONTAINER_INFRA_PREFIX:-quay.io/}prometheus/prometheus
        retention: 14d
---
apiVersion: batch/v1
kind: Job
metadata:
  name: install-${CHART_NAME}-job
  namespace: magnum-tiller
spec:
  backoffLimit: 5
  template:
    spec:
      serviceAccountName: tiller
      containers:
      - name: config-helm
        image: docker.io/openstackmagnum/helm-client:dev
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
