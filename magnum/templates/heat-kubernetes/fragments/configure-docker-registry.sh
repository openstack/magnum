#!/bin/sh

. /etc/sysconfig/heat-params

if [ "$REGISTRY_ENABLED" = "False" ]; then
    exit 0
fi

cat > /etc/sysconfig/registry-config.yaml << EOF
version 0.1
log:
  fields:
    service: registry
storage:
  cache:
    layerinfo: inmemory
  swift:
    authurl: $REGISTRY_AUTH_URL
    region: $REGISTRY_REGION
    username: $REGISTRY_USERNAME
    password: $REGISTRY_PASSWORD
    domain: $REGISTRY_DOMAIN
    trustid: $REGISTRY_TRUST_ID
    container: $REGISTRY_CONTAINER
    insecureskipverify: $REGISTRY_INSECURE
    chunksize: $REGISTRY_CHUNKSIZE
http:
    addr: localhost:5000
EOF

cat > /etc/systemd/system/registry.service << EOF
[Unit]
Description=Docker registry v2
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/usr/bin/docker run -d -p $REGISTRY_PORT:5000 --restart=always --name registry -v /etc/sysconfig/registry-config.yaml:/etc/docker/registry/config.yaml registry:2
ExecStop=/usr/bin/docker rm -f registry

[Install]
WantedBy=multi-user.target
EOF
