. /etc/sysconfig/heat-params

step="enable-helm-tiller"
printf "Starting to run ${step}\n"

if [ "$(echo ${TILLER_ENABLED} | tr '[:upper:]' '[:lower:]')" == "true" ]; then
    CERTS_DIR="/etc/kubernetes/helm/certs/"
    mkdir -p "${CERTS_DIR}"

    # Private CA key
    openssl genrsa -out "${CERTS_DIR}/ca.key.pem" 4096

    # CA public cert
    openssl req -key "${CERTS_DIR}/ca.key.pem" -new -x509 -days 7300 -sha256 -out "${CERTS_DIR}/ca.cert.pem" -extensions v3_ca -subj "/C=US/ST=Texas/L=Austin/O=OpenStack/OU=Magnum/CN=tiller"

    # Private tiller-server key
    openssl genrsa -out "${CERTS_DIR}/tiller.key.pem" 4096

    # Private helm-client key
    openssl genrsa -out "${CERTS_DIR}/helm.key.pem" 4096

    # Request for tiller-server cert
    openssl req -key "${CERTS_DIR}/tiller.key.pem" -new -sha256 -out "${CERTS_DIR}/tiller.csr.pem" -subj "/C=US/ST=Texas/L=Austin/O=OpenStack/OU=Magnum/CN=tiller-server"

    # Request for helm-client cert
    openssl req -key "${CERTS_DIR}/helm.key.pem" -new -sha256 -out "${CERTS_DIR}/helm.csr.pem" -subj "/C=US/ST=Texas/L=Austin/O=OpenStack/OU=Magnum/CN=helm-client"

    # Sign tiller-server cert
    openssl x509 -req -CA "${CERTS_DIR}/ca.cert.pem" -CAkey "${CERTS_DIR}/ca.key.pem" -CAcreateserial -in "${CERTS_DIR}/tiller.csr.pem" -out "${CERTS_DIR}/tiller.cert.pem" -days 365

    # Sign helm-client cert
    openssl x509 -req -CA "${CERTS_DIR}/ca.cert.pem" -CAkey "${CERTS_DIR}/ca.key.pem" -CAcreateserial -in "${CERTS_DIR}/helm.csr.pem" -out "${CERTS_DIR}/helm.cert.pem"  -days 365

    _tiller_prefix=${CONTAINER_INFRA_PREFIX:-gcr.io/kubernetes-helm/}
    TILLER_RBAC=/srv/magnum/kubernetes/manifests/tiller-rbac.yaml
    TILLER_DEPLOYER=/srv/magnum/kubernetes/manifests/deploy-tiller.yaml

    TILLER_IMAGE="${_tiller_prefix}tiller:${TILLER_TAG}"

    [ -f ${TILLER_RBAC} ] || {
        echo "Writing File: $TILLER_RBAC"
        mkdir -p $(dirname ${TILLER_RBAC})
        cat << EOF > ${TILLER_RBAC}
---
apiVersion: v1
kind: Namespace
metadata:
  name: ${TILLER_NAMESPACE}
---
# Tiller service account
apiVersion: v1
kind: ServiceAccount
metadata:
  name: tiller
  namespace: ${TILLER_NAMESPACE}
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: tiller
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: cluster-admin
subjects:
  - kind: ServiceAccount
    name: tiller
    namespace: ${TILLER_NAMESPACE}
EOF
    }

    [ -f ${TILLER_DEPLOYER} ] || {
        echo "Writing File: $TILLER_DEPLOYER"
        mkdir -p $(dirname ${TILLER_DEPLOYER})
        cat << EOF > ${TILLER_DEPLOYER}
---
apiVersion: apps/v1
kind: Deployment
metadata:
  creationTimestamp: null
  labels:
    app: helm
    name: tiller
  name: tiller-deploy
  namespace: ${TILLER_NAMESPACE}
spec:
  replicas: 1
  strategy: {}
  selector:
    matchLabels:
      app: helm
      name: tiller
  template:
    metadata:
      creationTimestamp: null
      labels:
        app: helm
        name: tiller
    spec:
      automountServiceAccountToken: true
      containers:
      - env:
        - name: TILLER_NAMESPACE
          value: ${TILLER_NAMESPACE}
        - name: TILLER_HISTORY_MAX
          value: "0"
        - name: TILLER_TLS_VERIFY
          value: "1"
        - name: TILLER_TLS_ENABLE
          value: "1"
        - name: TILLER_TLS_CERTS
          value: /etc/certs
        image: ${TILLER_IMAGE}
        imagePullPolicy: IfNotPresent
        livenessProbe:
          httpGet:
            path: /liveness
            port: 44135
          initialDelaySeconds: 1
          timeoutSeconds: 1
        name: tiller
        ports:
        - containerPort: 44134
          name: tiller
        - containerPort: 44135
          name: http
        readinessProbe:
          httpGet:
            path: /readiness
            port: 44135
          initialDelaySeconds: 1
          timeoutSeconds: 1
        resources:
          requests:
            cpu: 25m
        volumeMounts:
        - mountPath: /etc/certs
          name: tiller-certs
          readOnly: true
      serviceAccountName: tiller
      tolerations:
      # Make sure the pod can be scheduled on master kubelet.
      - effect: NoSchedule
        operator: Exists
      # Mark the pod as a critical add-on for rescheduling.
      - key: CriticalAddonsOnly
        operator: Exists
      - effect: NoExecute
        operator: Exists
      # run only on master nodes
      nodeSelector:
        node-role.kubernetes.io/master: ""
      volumes:
      - name: tiller-certs
        secret:
          secretName: tiller-secret
status: {}

---
apiVersion: v1
kind: Service
metadata:
  creationTimestamp: null
  labels:
    app: helm
    name: tiller
  name: tiller-deploy
  namespace: ${TILLER_NAMESPACE}
spec:
  ports:
  - name: tiller
    port: 44134
    targetPort: tiller
  selector:
    app: helm
    name: tiller
  type: ClusterIP
status:
  loadBalancer: {}

---
apiVersion: v1
kind: Secret
type: Opaque
metadata:
  creationTimestamp: null
  labels:
    app: helm
    name: tiller
  name: tiller-secret
  namespace: ${TILLER_NAMESPACE}
data:
  ca.crt: $(cat "${CERTS_DIR}/ca.cert.pem" | base64 --wrap=0)
  tls.crt: $(cat "${CERTS_DIR}/tiller.cert.pem" | base64 --wrap=0)
  tls.key: $(cat "${CERTS_DIR}/tiller.key.pem" | base64 --wrap=0)
---
apiVersion: v1
kind: Secret
type: Opaque
metadata:
  creationTimestamp: null
  labels:
    app: helm
    name: tiller-ca-key
  name: tiller-ca-key
  namespace: ${TILLER_NAMESPACE}
data:
  ca.key.pem: $(cat "${CERTS_DIR}/ca.key.pem" | base64 --wrap=0)
---
apiVersion: v1
kind: Secret
type: Opaque
metadata:
  creationTimestamp: null
  labels:
    app: helm
    name: helm-client
  name: helm-client-secret
  namespace: ${TILLER_NAMESPACE}
data:
  ca.pem: $(cat "${CERTS_DIR}/ca.cert.pem" | base64 --wrap=0)
  cert.pem: $(cat "${CERTS_DIR}/helm.cert.pem" | base64 --wrap=0)
  key.pem: $(cat "${CERTS_DIR}/helm.key.pem" | base64 --wrap=0)
EOF
    }

    until  [ "ok" = "$(kubectl get --raw='/healthz')" ]
    do
        echo "Waiting for Kubernetes API..."
        sleep 5
    done

    kubectl apply -f ${TILLER_RBAC}
    kubectl apply -f ${TILLER_DEPLOYER}
fi

printf "Finished running ${step}\n"
