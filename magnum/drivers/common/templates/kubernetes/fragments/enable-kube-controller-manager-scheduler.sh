#!/bin/sh

. /etc/sysconfig/heat-params

if [ -n "${INSECURE_REGISTRY_URL}" ]; then
    HYPERKUBE_IMAGE="${INSECURE_REGISTRY_URL}/google_containers/hyperkube:${KUBE_VERSION}"
else
    HYPERKUBE_IMAGE="gcr.io/google_containers/hyperkube:${KUBE_VERSION}"
fi

# vars also used by the Kubernetes config files
unset KUBE_API_PORT
unset KUBE_ALLOW_PRIV

# this function generate a list of args (one per line) from a list of possibly nested args
# the first parameter is the prefix to be added before each arg
# empty args are ignored
generate_pod_args() {
    prefix=$1

    for var in "${@:2}" ; do
        for arg in "$var" ; do
            echo "$prefix$arg"
        done
    done
}


init_templates () {
    . /etc/kubernetes/config

    . /etc/kubernetes/controller-manager

    local TEMPLATE=/etc/kubernetes/manifests/kube-controller-manager.yaml
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
  hostNetwork: true
  containers:
  - name: kube-controller-manager
    image: ${HYPERKUBE_IMAGE}
    command:
    - /hyperkube
    - controller-manager
    - --leader-elect=true
$(generate_pod_args "    - " $KUBE_LOGTOSTDERR $KUBE_LOG_LEVEL $KUBE_MASTER $KUBE_CONTROLLER_MANAGER_ARGS)
    livenessProbe:
      httpGet:
        host: 127.0.0.1
        path: /healthz
        port: 10252
      initialDelaySeconds: 15
      timeoutSeconds: 1
    volumeMounts:
    - mountPath: /etc/ssl/certs
      name: ssl-certs-host
      readOnly: true
    - mountPath: /srv/kubernetes
      name: kubernetes-config
      readOnly: true
    - mountPath: /etc/sysconfig
      name: sysconfig
      readOnly: true
  volumes:
  - hostPath:
      path: /etc/ssl/certs
    name: ssl-certs-host
  - hostPath:
      path: /srv/kubernetes
    name: kubernetes-config
  - hostPath:
      path: /etc/sysconfig
    name: sysconfig
EOF
    }

    . /etc/kubernetes/scheduler

    local TEMPLATE=/etc/kubernetes/manifests/kube-scheduler.yaml
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
    - --leader-elect=true
$(generate_pod_args "    - " $KUBE_LOGTOSTDERR $KUBE_LOG_LEVEL $KUBE_MASTER $KUBE_SCHEDULER_ARGS)
    livenessProbe:
      httpGet:
        host: 127.0.0.1
        path: /healthz
        port: 10251
      initialDelaySeconds: 15
      timeoutSeconds: 1
    volumeMounts:
    - mountPath: /etc/ssl/certs
      name: ssl-certs-host
      readOnly: true
    - mountPath: /srv/kubernetes
      name: kubernetes-config
      readOnly: true
    - mountPath: /etc/sysconfig
      name: sysconfig
      readOnly: true
  volumes:
  - hostPath:
      path: /etc/ssl/certs
    name: ssl-certs-host
  - hostPath:
      path: /srv/kubernetes
    name: kubernetes-config
  - hostPath:
      path: /etc/sysconfig
    name: sysconfig
EOF
    }
}

init_templates
