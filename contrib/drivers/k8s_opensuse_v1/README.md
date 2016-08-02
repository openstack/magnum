# Magnum openSUSE K8s driver

This is openSUSE Kubernetes driver for Magnum, which allow to deploy Kubernetes cluster on openSUSE.

## Installation

### 1. Install the openSUSE K8s driver in Magnum

- To install the driver, from this directory run:

       `python ./setup.py install`

### 2. Enable driver in magnum.conf

      enabled_definitions = ...,magnum_vm_opensuse_k8s

### 2. Restart Magnum

  Both Magnum services has to restarted `magnum-api` and `magnum-conductor`
