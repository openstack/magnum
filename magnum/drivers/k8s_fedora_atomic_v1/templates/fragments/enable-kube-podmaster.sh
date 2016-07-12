#!/bin/sh

. /etc/sysconfig/heat-params

if [ -n "${INSECURE_REGISTRY_URL}" ]; then
    PODMASTER_IMAGE="${INSECURE_REGISTRY_URL}/google_containers/podmaster:1.1"
    HYPERKUBE_IMAGE="${INSECURE_REGISTRY_URL}/google_containers/hyperkube:${KUBE_VERSION}"
else
    PODMASTER_IMAGE="gcr.io/google_containers/podmaster:1.1"
    HYPERKUBE_IMAGE="gcr.io/google_containers/hyperkube:${KUBE_VERSION}"
fi


init_templates () {
    local TEMPLATE=/etc/kubernetes/manifests/kube-podmaster.yaml
    [ -f ${TEMPLATE} ] || {
        echo "TEMPLATE: $TEMPLATE"
        mkdir -p $(dirname ${TEMPLATE})
        cat << EOF > ${TEMPLATE}
apiVersion: v1
kind: Pod
metadata:
  name: kube-podmaster
  namespace: kube-system
spec:
  hostNetwork: true
  containers:
  - name: scheduler-elector
    image: ${PODMASTER_IMAGE}
    command:
    - /podmaster
    - --etcd-servers=http://127.0.0.1:2379
    - --key=scheduler
    - --source-file=/src/manifests/kube-scheduler.yaml
    - --dest-file=/dst/manifests/kube-scheduler.yaml
    volumeMounts:
    - mountPath: /src/manifests
      name: manifest-src
      readOnly: true
    - mountPath: /dst/manifests
      name: manifest-dst
  - name: controller-manager-elector
    image: ${PODMASTER_IMAGE}
    command:
    - /podmaster
    - --etcd-servers=http://127.0.0.1:2379
    - --key=controller
    - --source-file=/src/manifests/kube-controller-manager.yaml
    - --dest-file=/dst/manifests/kube-controller-manager.yaml
    terminationMessagePath: /dev/termination-log
    volumeMounts:
    - mountPath: /src/manifests
      name: manifest-src
      readOnly: true
    - mountPath: /dst/manifests
      name: manifest-dst
  volumes:
  - hostPath:
      path: /srv/kubernetes/manifests
    name: manifest-src
  - hostPath:
      path: /etc/kubernetes/manifests
    name: manifest-dst
EOF
    }

    local SERVICE_ACCOUNT_PRIVATE_KEY_FILE=/etc/kubernetes/ssl/server.key
    local ROOT_CA_FILE=/etc/kubernetes/ssl/ca.crt

    if [ "${TLS_DISABLED}" = "True" ]; then
        SERVICE_ACCOUNT_PRIVATE_KEY_FILE=
        ROOT_CA_FILE=
    fi

    local TEMPLATE=/srv/kubernetes/manifests/kube-controller-manager.yaml
    [ -f ${TEMPLATE} ] || {
        echo "TEMPLATE: $TEMPLATE"
        mkdir -p $(dirname ${TEMPLATE})
        cat << EOF > ${TEMPLATE}
apiVersion: v1
kind: Pod
metadata:
  name: kube-controller-manager
  namespace: kube-system
spec:
  containers:
  - name: kube-controller-manager
    image: ${HYPERKUBE_IMAGE}
    command:
    - /hyperkube
    - controller-manager
    - --master=http://127.0.0.1:8080
    - --service-account-private-key-file=${SERVICE_ACCOUNT_PRIVATE_KEY_FILE}
    - --root-ca-file=${ROOT_CA_FILE}
    livenessProbe:
      httpGet:
        host: 127.0.0.1
        path: /healthz
        port: 10252
      initialDelaySeconds: 15
      timeoutSeconds: 1
    volumeMounts:
    - mountPath: /etc/kubernetes/ssl
      name: ssl-certs-kubernetes
      readOnly: true
    - mountPath: /etc/ssl/certs
      name: ssl-certs-host
      readOnly: true
  hostNetwork: true
  volumes:
  - hostPath:
      path: /srv/kubernetes
    name: ssl-certs-kubernetes
  - hostPath:
      path: /etc/ssl/certs
    name: ssl-certs-host
EOF
    }

    local TEMPLATE=/srv/kubernetes/manifests/kube-scheduler.yaml
    [ -f ${TEMPLATE} ] || {
        echo "TEMPLATE: $TEMPLATE"
        mkdir -p $(dirname ${TEMPLATE})
        cat << EOF > ${TEMPLATE}
apiVersion: v1
kind: Pod
metadata:
  name: kube-scheduler
  namespace: kube-system
spec:
  hostNetwork: true
  containers:
  - name: kube-scheduler
    image: ${HYPERKUBE_IMAGE}
    command:
    - /hyperkube
    - scheduler
    - --master=http://127.0.0.1:8080
    livenessProbe:
      httpGet:
        host: 127.0.0.1
        path: /healthz
        port: 10251
      initialDelaySeconds: 15
      timeoutSeconds: 1
EOF
    }
}

init_templates
