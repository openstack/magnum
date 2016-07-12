#!/bin/sh

# this service is required because docker will start only after cloud init was finished
# due to the service dependencies in Fedora Atomic (docker <- docker-storage-setup <- cloud-final)


. /etc/sysconfig/heat-params

if [ -n "${INSECURE_REGISTRY_URL}" ]; then
    KUBEUI_IMAGE="${INSECURE_REGISTRY_URL}/google_containers/kube-ui:v4"
else
    KUBEUI_IMAGE="gcr.io/google_containers/kube-ui:v4"
fi

KUBE_UI_RC=/srv/kubernetes/manifests/kube-ui-rc.yaml

[ -f ${KUBE_UI_RC} ] || {
    echo "Writing File: $KUBE_UI_RC"
    mkdir -p $(dirname ${KUBE_UI_RC})
    cat << EOF > ${KUBE_UI_RC}
apiVersion: v1
kind: ReplicationController
metadata:
  name: kube-ui-v4
  namespace: kube-system
  labels:
    k8s-app: kube-ui
    version: v4
    kubernetes.io/cluster-service: "true"
spec:
  replicas: 1
  selector:
    k8s-app: kube-ui
    version: v4
  template:
    metadata:
      labels:
        k8s-app: kube-ui
        version: v4
        kubernetes.io/cluster-service: "true"
    spec:
      containers:
      - name: kube-ui
        image: ${KUBEUI_IMAGE}
        resources:
          limits:
            cpu: 100m
            memory: 50Mi
        ports:
        - containerPort: 8080
EOF
}

KUBE_UI_SVC=/srv/kubernetes/manifests/kube-ui-svc.yaml
[ -f ${KUBE_UI_SVC} ] || {
    echo "Writing File: $KUBE_UI_SVC"
    mkdir -p $(dirname ${KUBE_UI_SVC})
    cat << EOF > ${KUBE_UI_SVC}
apiVersion: v1
kind: Service
metadata:
  name: kube-ui
  namespace: kube-system
  labels:
    k8s-app: kube-ui
    kubernetes.io/cluster-service: "true"
    kubernetes.io/name: "KubeUI"
spec:
  selector:
    k8s-app: kube-ui
  ports:
  - port: 80
    targetPort: 8080
EOF
}

KUBE_UI_BIN=/usr/local/bin/kube-ui
[ -f ${KUBE_UI_BIN} ] || {
    echo "Writing File: $KUBE_UI_BIN"
    mkdir -p $(dirname ${KUBE_UI_BIN})
    cat << EOF > ${KUBE_UI_BIN}
#!/bin/sh
until curl -sf "http://127.0.0.1:8080/healthz"
do
    echo "Waiting for Kubernetes API..."
    sleep 5
done

/usr/bin/kubectl create -f /srv/kubernetes/manifests/kube-ui-rc.yaml --namespace=kube-system
/usr/bin/kubectl create -f /srv/kubernetes/manifests/kube-ui-svc.yaml --namespace=kube-system
EOF
}

KUBE_UI_SERVICE=/etc/systemd/system/kube-ui.service
[ -f ${KUBE_UI_SERVICE} ] || {
    echo "Writing File: $KUBE_UI_SERVICE"
    mkdir -p $(dirname ${KUBE_UI_SERVICE})
    cat << EOF > ${KUBE_UI_SERVICE}
[Unit]
After=kube-system-namespace
Requires=kubelet.service
Requires=kube-system-namespace.service

[Service]
Type=oneshot
EnvironmentFile=-/etc/kubernetes/config
ExecStart=${KUBE_UI_BIN}

[Install]
WantedBy=multi-user.target
EOF
}

chown root:root ${KUBE_UI_BIN}
chmod 0755 ${KUBE_UI_BIN}

chown root:root ${KUBE_UI_SERVICE}
chmod 0644 ${KUBE_UI_SERVICE}

systemctl enable kube-ui
systemctl start --no-block kube-ui
