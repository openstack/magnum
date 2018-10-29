#!/bin/sh

. /etc/kubernetes/proxy
. /etc/kubernetes/config

ARGS="$@ $KUBE_LOGTOSTDERR $KUBE_LOG_LEVEL $KUBE_MASTER $KUBE_PROXY_ARGS"

exec /usr/local/bin/kube-proxy $ARGS
