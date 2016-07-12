#!/bin/sh

# this service required because docker will start only after cloud init was finished
# due service dependencies at Fedora Atomic (docker <- docker-storage-setup <- cloud-final)

. /etc/sysconfig/heat-params

KUBE_SYSTEM_JSON=/srv/kubernetes/kube-system-namespace.json
[ -f ${KUBE_SYSTEM_JSON} ] || {
    echo "Writing File: $KUBE_SYSTEM_JSON"
    mkdir -p $(dirname ${KUBE_SYSTEM_JSON})
    cat << EOF > ${KUBE_SYSTEM_JSON}
{
  "apiVersion": "v1",
  "kind": "Namespace",
  "metadata": {
    "name": "kube-system"
  }
}
EOF
}

KUBE_SYSTEM_BIN=/usr/local/bin/kube-system-namespace
[ -f ${KUBE_SYSTEM_BIN} ] || {
    echo "Writing File: $KUBE_SYSTEM_BIN"
    mkdir -p $(dirname ${KUBE_SYSTEM_BIN})
    cat << EOF > ${KUBE_SYSTEM_BIN}
#!/bin/sh
until curl -sf "http://127.0.0.1:8080/healthz"
do
    echo "Waiting for Kubernetes API..."
    sleep 5
done

/usr/bin/kubectl create -f /srv/kubernetes/kube-system-namespace.json
EOF
}

KUBE_SYSTEM_SERVICE=/etc/systemd/system/kube-system-namespace.service
[ -f ${KUBE_SYSTEM_SERVICE} ] || {
    echo "Writing File: $KUBE_SYSTEM_SERVICE"
    mkdir -p $(dirname ${KUBE_SYSTEM_SERVICE})
    cat << EOF > ${KUBE_SYSTEM_SERVICE}
[Unit]
After=kubelet.service
Requires=kubelet.service

[Service]
Type=oneshot
Environment=HOME=/root
EnvironmentFile=-/etc/kubernetes/config
ExecStart=${KUBE_SYSTEM_BIN}

[Install]
WantedBy=multi-user.target
EOF
}

chown root:root ${KUBE_SYSTEM_BIN}
chmod 0755 ${KUBE_SYSTEM_BIN}

chown root:root ${KUBE_SYSTEM_SERVICE}
chmod 0644 ${KUBE_SYSTEM_SERVICE}

systemctl enable kube-system-namespace
systemctl start --no-block kube-system-namespace
