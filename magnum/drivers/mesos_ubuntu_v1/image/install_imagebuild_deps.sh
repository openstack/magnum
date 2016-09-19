#!/bin/bash

# This script installs all needed dependencies to generate
# images using diskimage-builder. Please not it only has been
# tested on Ubuntu Trusty

set -eux
set -o pipefail

sudo apt-get update || true
sudo apt-get install -y \
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
    wget
