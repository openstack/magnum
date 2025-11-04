#!/bin/sh

step="export-kubeconfig"
printf "Starting to run ${step}\n"

export KUBECONFIG=/etc/kubernetes/admin.conf