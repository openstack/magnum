#!/bin/bash

. /etc/sysconfig/heat-params

set -ex

step="prometheus-adapter"
printf "Starting to run ${step}\n"

### Configuration
###############################################################################
CHART_NAME="prometheus-adapter"


if [ "$(echo ${MONITORING_ENABLED} | tr '[:upper:]' '[:lower:]')" = "true" ] && \
   [ "$(echo ${PROMETHEUS_ADAPTER_ENABLED} | tr '[:upper:]' '[:lower:]')" = "true" ]; then

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
        helm install stable/${CHART_NAME} --namespace kube-system --name ${CHART_NAME} --version ${PROMETHEUS_ADAPTER_CHART_TAG} --values /opt/magnum/install-${CHART_NAME}-values.yaml
    fi

  install-${CHART_NAME}-values.yaml:  |
    image:
      repository: ${CONTAINER_INFRA_PREFIX:-docker.io/directxman12/}k8s-prometheus-adapter-${ARCH}

    priorityClassName: "system-cluster-critical"

    prometheus:
      url: http://web.tcp.prometheus-prometheus.kube-system.svc.cluster.local

    resources:
      requests:
        cpu: 150m
        memory: 400Mi

    rules:
      existing: ${PROMETHEUS_ADAPTER_CONFIGMAP}

    # tls:
    #   enable: true
    #   ca: |-
    #     # Public CA file that signed the APIService
    #   key: |-
    #     # Private key of the APIService
    #   certificate: |-
    #     # Public key of the APIService

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
