#!/bin/bash

set -o xtrace
set -o errexit

# Setup Docker repo and add signing key
sudo apt-get update
sudo apt-get install -y \
    apt-transport-https \
    ca-certificates \
    curl \
    software-properties-common
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -
sudo add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable"
sudo apt-get update
sudo apt-get -y install --no-install-recommends docker-ce

sudo systemctl start docker --now

sudo docker info

sudo apt-get install python-pip

sudo pip install docker

echo "Completed $0."
