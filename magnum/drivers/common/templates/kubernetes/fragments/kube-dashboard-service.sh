#!/bin/sh

# this service is required because docker will start only after cloud init was finished
# due to the service dependencies in Fedora Atomic (docker <- docker-storage-setup <- cloud-final)


. /etc/sysconfig/heat-params

if [ "$(echo $KUBE_DASHBOARD_ENABLED | tr '[:upper:]' '[:lower:]')" == "false" ]; then
    exit 0
fi

KUBE_DASH_IMAGE="${CONTAINER_INFRA_PREFIX:-gcr.io/google_containers/}kubernetes-dashboard-amd64:${KUBE_DASHBOARD_VERSION}"

KUBE_DASH_DEPLOY=/srv/kubernetes/manifests/kube-dash-deploy.yaml

[ -f ${KUBE_DASH_DEPLOY} ] || {
    echo "Writing File: $KUBE_DASH_DEPLOY"
    mkdir -p $(dirname ${KUBE_DASH_DEPLOY})
    cat << EOF > ${KUBE_DASH_DEPLOY}
kind: Deployment
apiVersion: extensions/v1beta1
metadata:
  labels:
    app: kubernetes-dashboard
  name: kubernetes-dashboard
  namespace: kube-system
spec:
  replicas: 1
  revisionHistoryLimit: 10
  selector:
    matchLabels:
      app: kubernetes-dashboard
  template:
    metadata:
      labels:
        app: kubernetes-dashboard
      # Comment the following annotation if Dashboard must not be deployed on master
      annotations:
        scheduler.alpha.kubernetes.io/tolerations: |
          [
            {
              "key": "dedicated",
              "operator": "Equal",
              "value": "master",
              "effect": "NoSchedule"
            }
          ]
    spec:
      containers:
      - name: kubernetes-dashboard
        image: ${KUBE_DASH_IMAGE}
        imagePullPolicy: Always
        ports:
        - containerPort: 9090
          protocol: TCP
        args:
        livenessProbe:
          httpGet:
            path: /
            port: 9090
          initialDelaySeconds: 30
          timeoutSeconds: 30
EOF
}

KUBE_DASH_SVC=/srv/kubernetes/manifests/kube-dash-svc.yaml
[ -f ${KUBE_DASH_SVC} ] || {
    echo "Writing File: $KUBE_DASH_SVC"
    mkdir -p $(dirname ${KUBE_DASH_SVC})
    cat << EOF > ${KUBE_DASH_SVC}
kind: Service
apiVersion: v1
metadata:
  labels:
    app: kubernetes-dashboard
  name: kubernetes-dashboard
  namespace: kube-system
spec:
  type: NodePort
  ports:
  - port: 80
    targetPort: 9090
  selector:
    app: kubernetes-dashboard
EOF
}

KUBE_DASH_BIN=/usr/local/bin/kube-dash
[ -f ${KUBE_DASH_BIN} ] || {
    echo "Writing File: $KUBE_DASH_BIN"
    mkdir -p $(dirname ${KUBE_DASH_BIN})
    cat << EOF > ${KUBE_DASH_BIN}
#!/bin/sh
until curl -sf "http://127.0.0.1:8080/healthz"
do
    echo "Waiting for Kubernetes API..."
    sleep 5
done

#echo check for existence of kubernetes-dashboard deployment
/usr/bin/kubectl get deployment kubernetes-dashboard --namespace=kube-system

if [ "\$?" != "0" ]; then
    /usr/bin/kubectl create -f /srv/kubernetes/manifests/kube-dash-deploy.yaml --namespace=kube-system
fi

#echo check for existence of kubernetes-dashboard service
/usr/bin/kubectl get service kubernetes-dashboard --namespace=kube-system

if [ "\$?" != "0" ]; then
    /usr/bin/kubectl create -f /srv/kubernetes/manifests/kube-dash-svc.yaml --namespace=kube-system
fi
EOF
}

KUBE_DASH_SERVICE=/etc/systemd/system/kube-dash.service
[ -f ${KUBE_DASH_SERVICE} ] || {
    echo "Writing File: $KUBE_DASH_SERVICE"
    mkdir -p $(dirname ${KUBE_DASH_SERVICE})
    cat << EOF > ${KUBE_DASH_SERVICE}
[Unit]
Description=Enable kubernetes dashboard

[Service]
Type=oneshot
Environment=HOME=/root
EnvironmentFile=-/etc/kubernetes/config
ExecStart=${KUBE_DASH_BIN}

[Install]
WantedBy=multi-user.target
EOF
}

chown root:root ${KUBE_DASH_BIN}
chmod 0755 ${KUBE_DASH_BIN}

chown root:root ${KUBE_DASH_SERVICE}
chmod 0644 ${KUBE_DASH_SERVICE}

systemctl enable kube-dash
systemctl start --no-block kube-dash
