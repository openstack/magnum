INGRESS_TRAEFIK_MANIFEST=/srv/magnum/kubernetes/ingress-traefik.yaml
INGRESS_TRAEFIK_MANIFEST_CONTENT=$(cat <<EOF
---
kind: ConfigMap
apiVersion: v1
metadata:
  name: ingress-traefik
  namespace: kube-system
  labels:
    k8s-app: ingress-traefik-backend
data:
  traefik.toml: |-
    logLevel = "INFO"
    defaultEntryPoints = ["http", "https"]
    [metrics]
      [metrics.prometheus]
        entryPoint = "metrics"
    [api]
    [kubernetes]
    [entryPoints]
      [entryPoints.http]
        address = ":80"
      [entryPoints.https]
        address = ":443"
        [entryPoints.https.tls]
          minVersion = "VersionTLS12"
          cipherSuites = [
            "TLS_ECDHE_ECDSA_WITH_CHACHA20_POLY1305",
            "TLS_ECDHE_RSA_WITH_CHACHA20_POLY1305",
            "TLS_ECDHE_ECDSA_WITH_AES_256_GCM_SHA384",
            "TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384",
            "TLS_ECDHE_ECDSA_WITH_AES_128_GCM_SHA256",
            "TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256",
            "TLS_ECDHE_RSA_WITH_AES_128_CBC_SHA256",
            "TLS_ECDHE_ECDSA_WITH_AES_128_CBC_SHA256",
            "TLS_ECDHE_RSA_WITH_AES_256_CBC_SHA",
            "TLS_ECDHE_RSA_WITH_AES_128_CBC_SHA",
            "TLS_ECDHE_ECDSA_WITH_AES_256_CBC_SHA",
            "TLS_ECDHE_ECDSA_WITH_AES_128_CBC_SHA",
            "TLS_RSA_WITH_AES_256_GCM_SHA384",
            "TLS_RSA_WITH_AES_128_GCM_SHA256",
            "TLS_RSA_WITH_AES_128_CBC_SHA256",
            "TLS_RSA_WITH_AES_256_CBC_SHA",
            "TLS_RSA_WITH_AES_128_CBC_SHA"
          ]
      [entryPoints.metrics]
        address = ":8082"
---
kind: DaemonSet
apiVersion: apps/v1
metadata:
  name: ingress-traefik
  namespace: kube-system
  labels:
    k8s-app: ingress-traefik-backend
spec:
  selector:
    matchLabels:
      k8s-app: ingress-traefik-backend
      name: ingress-traefik-backend
  template:
    metadata:
      labels:
        k8s-app: ingress-traefik-backend
        name: ingress-traefik-backend
    spec:
      serviceAccountName: ingress-traefik
      terminationGracePeriodSeconds: 60
      hostNetwork: true
      containers:
      - image: ${CONTAINER_INFRA_PREFIX:-docker.io/}traefik:${TRAEFIK_INGRESS_CONTROLLER_TAG}
        name: ingress-traefik-backend
        resources:
          requests:
            cpu: 100m
            memory: 50Mi
        ports:
        - name: http
          containerPort: 80
          hostPort: 80
        - name: https
          containerPort: 443
          hostPort: 443
        - name: admin
          containerPort: 8080
        - name: metrics
          containerPort: 8082
        securityContext:
          capabilities:
            drop:
            - ALL
            add:
            - NET_BIND_SERVICE
        volumeMounts:
        - name: ingress-traefik
          mountPath: /etc/traefik/traefik.toml
          subPath: traefik.toml
      volumes:
      - name: ingress-traefik
        configMap:
          name: ingress-traefik
      nodeSelector:
        role: ${INGRESS_CONTROLLER_ROLE}
---
kind: Service
apiVersion: v1
metadata:
  name: ingress-traefik
  namespace: kube-system
  labels:
    k8s-app: traefik
spec:
  selector:
    k8s-app: ingress-traefik-backend
  ports:
    - name: http
      protocol: TCP
      port: 80
    - name: https
      protocol: TCP
      port: 443
    - name: admin
      protocol: TCP
      port: 8080
    - name: metrics
      port: 9100
      protocol: TCP
      targetPort: metrics
---
kind: ClusterRole
apiVersion: rbac.authorization.k8s.io/v1
metadata:
  name: ingress-traefik
rules:
  - apiGroups:
      - ""
    resources:
      - services
      - endpoints
      - secrets
    verbs:
      - get
      - list
      - watch
  - apiGroups:
      - extensions
    resources:
      - ingresses
    verbs:
      - get
      - list
      - watch
---
kind: ClusterRoleBinding
apiVersion: rbac.authorization.k8s.io/v1
metadata:
  name: ingress-traefik
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: ingress-traefik
subjects:
- kind: ServiceAccount
  name: ingress-traefik
  namespace: kube-system
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: ingress-traefik
  namespace: kube-system
EOF
)

writeFile $INGRESS_TRAEFIK_MANIFEST "$INGRESS_TRAEFIK_MANIFEST_CONTENT"

until  [ "ok" = "$(kubectl get --raw='/healthz')" ]
do
    echo "Waiting for Kubernetes API..."
    sleep 5
done

kubectl apply -f ${INGRESS_TRAEFIK_MANIFEST}
