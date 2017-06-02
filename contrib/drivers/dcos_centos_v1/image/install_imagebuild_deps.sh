#!/bin/bash

# This script installs all needed dependencies to generate
# images using diskimage-builder. Please note it only has been
# tested on Ubuntu Xenial.

set -eux
set -o pipefail

sudo apt update || true
sudo apt install -y \
    git \
    qemu-utils \
    python-dev \
    python-yaml \
    python-six \
    uuid-runtime \
    curl \
    sudo \
    kpartx \
    parted \
    wget \
    xfsprogs \
    yum \
    yum-utils
