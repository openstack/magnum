#!/bin/sh

. /etc/kubernetes/kubelet
. /etc/kubernetes/config

TEMP_KUBELET_ARGS='--cgroups-per-qos=false --enforce-node-allocatable='

ARGS="$@ $TEMP_KUBELET_ARGS $KUBE_LOGTOSTDERR $KUBE_LOG_LEVEL $KUBELET_API_SERVER $KUBELET_ADDRESS $KUBELET_PORT $KUBELET_HOSTNAME $KUBE_ALLOW_PRIV $KUBELET_ARGS"

ARGS=$(echo $ARGS | sed s/--cadvisor-port=0//)
ARGS=$(echo $ARGS | sed s/--require-kubeconfig//)
ARGS=$(echo $ARGS | sed s/node-role/node/)

exec /hyperkube kubelet $ARGS --containerized
