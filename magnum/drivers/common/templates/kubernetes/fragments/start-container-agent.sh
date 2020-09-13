set -x
set +u
HTTP_PROXY="$HTTP_PROXY"
HTTPS_PROXY="$HTTPS_PROXY"
NO_PROXY="$NO_PROXY"
CONTAINER_INFRA_PREFIX="$CONTAINER_INFRA_PREFIX"
HEAT_CONTAINER_AGENT_TAG="$HEAT_CONTAINER_AGENT_TAG"


if [ -n "${HTTP_PROXY}" ]; then
    export HTTP_PROXY
    echo "http_proxy=${HTTP_PROXY}" >> /etc/environment
fi

if [ -n "${HTTPS_PROXY}" ]; then
    export HTTPS_PROXY
    echo "https_proxy=${HTTPS_PROXY}" >> /etc/environment
fi

if [ -n "${NO_PROXY}" ]; then
    export NO_PROXY
    echo "no_proxy=${NO_PROXY}" >> /etc/environment
fi

# Create a keypair for the heat-container-agent to
# access the node over ssh. It is useful to operate
# in host mount namespace and apply configuration.
mkdir -p /srv/magnum/.ssh
chmod 700 /srv/magnum/.ssh
ssh-keygen -q -t rsa -N '' -f /srv/magnum/.ssh/heat_agent_rsa
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
# Security enhancement: Disable password authentication
sed -i '/^PasswordAuthentication yes/ s/ yes/ no/' /etc/ssh/sshd_config

systemctl restart sshd


_prefix="${CONTAINER_INFRA_PREFIX:-docker.io/openstackmagnum/}"

if [ "$(echo $USE_PODMAN | tr '[:upper:]' '[:lower:]')" == "true" ]; then
    cat > /etc/containers/libpod.conf <<EOF
# Maximum size of log files (in bytes)
# -1 is unlimited
# 50m
max_log_size = 52428800
EOF
    cat > /etc/systemd/system/heat-container-agent.service <<EOF
[Unit]
Description=Run heat-container-agent
After=network-online.target
Wants=network-online.target

[Service]
ExecStartPre=mkdir -p /var/lib/heat-container-agent
ExecStartPre=mkdir -p /var/run/heat-config
ExecStartPre=mkdir -p /var/run/os-collect-config
ExecStartPre=mkdir -p /opt/stack/os-config-refresh
ExecStartPre=mkdir -p /srv/magnum
ExecStartPre=-/bin/podman kill heat-container-agent
ExecStartPre=-/bin/podman rm heat-container-agent
ExecStartPre=-/bin/podman pull ${_prefix}heat-container-agent:${HEAT_CONTAINER_AGENT_TAG}
ExecStart=/bin/podman run \\
    --name heat-container-agent \\
    --net=host \\
    --privileged \\
    --volume /srv/magnum:/srv/magnum \\
    --volume /opt/stack/os-config-refresh:/opt/stack/os-config-refresh \\
    --volume /run/systemd:/run/systemd \\
    --volume /etc/:/etc/ \\
    --volume /var/lib:/var/lib \\
    --volume /var/run:/var/run \\
    --volume /var/log:/var/log \\
    --volume /tmp:/tmp \\
    --volume /dev:/dev \\
    --env REQUESTS_CA_BUNDLE=/etc/pki/tls/certs/ca-bundle.crt \\
    ${_prefix}heat-container-agent:${HEAT_CONTAINER_AGENT_TAG} \\
    /usr/bin/start-heat-container-agent
ExecStop=/bin/podman stop heat-container-agent
TimeoutStartSec=10min

[Install]
WantedBy=multi-user.target
EOF
else
    atomic install \
    --storage ostree \
    --system \
    --system-package no \
    --set REQUESTS_CA_BUNDLE=/etc/pki/tls/certs/ca-bundle.crt \
    --name heat-container-agent \
    "${_prefix}heat-container-agent:${HEAT_CONTAINER_AGENT_TAG}"
fi

systemctl enable heat-container-agent
systemctl start heat-container-agent
