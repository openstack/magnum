#!/bin/sh
# This shell script will do some extra configure stuff before running services

echo "configuring swarm ..."

# Add --storage-driver devicemapper to DOCKER_STORAGE_OPTIONS
sed -i '/^DOCKER_STORAGE_OPTIONS=/ s/=.*/=--storage-driver devicemapper --storage-opt dm.fs=xfs --storage-opt dm.datadev=\/dev\/mapper\/atomicos-docker--data --storage-opt dm.metadatadev=\/dev\/mapper\/atomicos-docker--meta/' /etc/sysconfig/docker-storage
