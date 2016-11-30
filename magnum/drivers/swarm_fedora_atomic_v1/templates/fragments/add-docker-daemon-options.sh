#!/bin/sh

. /etc/sysconfig/heat-params

opts="-H fd:// -H tcp://0.0.0.0:2375 "

if [ "$TLS_DISABLED" = 'False' ]; then
    opts=$opts"--tlsverify --tlscacert=/etc/docker/ca.crt "
    opts=$opts"--tlskey=/etc/docker/server.key "
    opts=$opts"--tlscert=/etc/docker/server.crt "
fi

sed -i '/^OPTIONS=/ s#\(OPTIONS='"'"'\)#\1'"$opts"'#' /etc/sysconfig/docker
