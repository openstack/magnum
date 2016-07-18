#!/bin/sh

# Start agent services
for service in docker mesos-agent; do
    echo "starting service $service"
    service $service start
    rm -f /etc/init/$service.override
done
