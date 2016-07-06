#!/bin/sh

. /etc/sysconfig/heat-params

if [ "$REGISTRY_ENABLED" = "False" ]; then
    exit 0
fi

cat > /etc/sysconfig/registry-config.yml << EOF
version: 0.1
log:
  fields:
    service: registry
storage:
  cache:
    layerinfo: inmemory
  swift:
    authurl: "$AUTH_URL"
    region: "$SWIFT_REGION"
    username: "$TRUSTEE_USERNAME"
    password: "$TRUSTEE_PASSWORD"
    domainid: "$TRUSTEE_DOMAIN_ID"
    trustid: "$TRUST_ID"
    container: "$REGISTRY_CONTAINER"
    insecureskipverify: $REGISTRY_INSECURE
    chunksize: $REGISTRY_CHUNKSIZE
http:
    addr: :5000
EOF

cat > /etc/systemd/system/registry.service << EOF
[Unit]
Description=Docker registry v2
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/usr/bin/docker run -d -p $REGISTRY_PORT:5000 --restart=always --name registry -v /etc/sysconfig/registry-config.yml:/etc/docker/registry/config.yml registry:2
ExecStop=/usr/bin/docker rm -f registry

[Install]
WantedBy=multi-user.target
EOF
