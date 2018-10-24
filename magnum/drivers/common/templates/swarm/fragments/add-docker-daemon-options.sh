#!/bin/sh

. /etc/sysconfig/heat-params

opts="-H fd:// -H tcp://0.0.0.0:2375 "

if [ "$TLS_DISABLED" = 'False' ]; then
    opts=$opts"--tlsverify --tlscacert=/etc/docker/ca.crt "
    opts=$opts"--tlskey=/etc/docker/server.key "
    opts=$opts"--tlscert=/etc/docker/server.crt "
fi

sed -i '/^OPTIONS=/ s#\(OPTIONS='"'"'\)#\1'"$opts"'#' /etc/sysconfig/docker

# NOTE(tobias-urdin): The live restore option is only for standalone daemons.
# If its specified the swarm init will fail so we remove it here.
# See: https://docs.docker.com/config/containers/live-restore
sed -i 's/\ --live-restore//g' /etc/sysconfig/docker
