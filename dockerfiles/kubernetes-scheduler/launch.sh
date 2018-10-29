#!/bin/sh

. /etc/kubernetes/scheduler
. /etc/kubernetes/config

ARGS="$@ $KUBE_LOGTOSTDERR $KUBE_LOG_LEVEL $KUBE_MASTER $KUBE_SCHEDULER_ARGS"

exec /usr/local/bin/kube-scheduler $ARGS
