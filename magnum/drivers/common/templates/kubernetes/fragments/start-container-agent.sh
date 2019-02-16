#!/bin/bash

. /etc/sysconfig/heat-params

set -uxe

if [ ! -z "$HTTP_PROXY" ]; then
    export HTTP_PROXY
fi

if [ ! -z "$HTTPS_PROXY" ]; then
    export HTTPS_PROXY
fi

if [ ! -z "$NO_PROXY" ]; then
    export NO_PROXY
fi

# Create a keypair for the heat-container-agent to
# access the node over ssh. It is useful to operate
# in host mount namespace and apply configuration.
mkdir -p /srv/magnum/.ssh
chmod 700 /srv/magnum/.ssh
ssh-keygen -t rsa -N '' -f /srv/magnum/.ssh/heat_agent_rsa
chmod 400 /srv/magnum/.ssh/heat_agent_rsa
chmod 400 /srv/magnum/.ssh/heat_agent_rsa.pub
# Add the public to the host authorized_keys file.
cat /srv/magnum/.ssh/heat_agent_rsa.pub > /root/.ssh/authorized_keys
# Add localost to know_hosts
ssh-keyscan 127.0.0.1 > /srv/magnum/.ssh/known_hosts
# ssh configguration file, to be specified with ssh -F
cat > /srv/magnum/.ssh/config <<EOF
Host localhost
     HostName 127.0.0.1
     User root
     IdentityFile /srv/magnum/.ssh/heat_agent_rsa
     UserKnownHostsFile /srv/magnum/.ssh/known_hosts
EOF

sed -i '/^PermitRootLogin/ s/ .*/ without-password/' /etc/ssh/sshd_config
systemctl restart sshd


_prefix=${CONTAINER_INFRA_PREFIX:-docker.io/openstackmagnum/}
atomic install \
--storage ostree \
--system \
--system-package no \
--set REQUESTS_CA_BUNDLE=/etc/pki/tls/certs/ca-bundle.crt \
--name heat-container-agent \
${_prefix}heat-container-agent:${HEAT_CONTAINER_AGENT_TAG}

systemctl start heat-container-agent
