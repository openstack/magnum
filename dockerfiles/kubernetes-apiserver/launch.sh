#!/bin/sh

. /etc/kubernetes/apiserver
. /etc/kubernetes/config

ARGS="$@ $KUBE_LOGTOSTDERR $KUBE_LOG_LEVEL $KUBE_ETCD_SERVERS $KUBE_API_ADDRESS $KUBE_API_PORT $KUBELET_PORT $KUBE_ALLOW_PRIV $KUBE_SERVICE_ADDRESSES $KUBE_ADMISSION_CONTROL $KUBE_API_ARGS"

ARGS=$(echo $ARGS | sed s#--tls-ca-file=/etc/kubernetes/certs/ca.crt##)
# KubeletPluginsWatcher=true,
ARGS=$(echo $ARGS | sed s/KubeletPluginsWatcher=true,//)

exec /usr/local/bin/kube-apiserver $ARGS
