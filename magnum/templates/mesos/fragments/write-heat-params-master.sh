#!/bin/sh

mkdir -p /etc/sysconfig
cat > /etc/sysconfig/heat-params <<EOF
MESOS_MASTERS_IPS="$MESOS_MASTERS_IPS"
CLUSTER_NAME="$CLUSTER_NAME"
QUORUM="$((($NUMBER_OF_MASTERS+1)/2))"
EOF
