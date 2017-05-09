#!/bin/sh
# Add rexray volume driver support for Swarm
. /etc/sysconfig/heat-params

set -e
set -x

# if no voulume driver is selected don't do any configuration
if [ -z "$VOLUME_DRIVER" ]; then
    exit 0
fi

mkdir -p /etc/rexray
mkdir -p /var/log/rexray
mkdir -p /var/run/rexray
mkdir -p /var/lib/rexray

REXRAY_CONFIG=/etc/rexray/config.yml

# Add rexray configuration
cat > $REXRAY_CONFIG <<EOF
libstorage:
  logging:
    level: info
  service: openstack
  integration:
    volume:
      operations:
        mount:
          preempt: $REXRAY_PREEMPT
openstack:
  authUrl:  $AUTH_URL
  userID:   $TRUSTEE_USER_ID
  password: $TRUSTEE_PASSWORD
  trustID:  $TRUST_ID
EOF

if [ ! -f /usr/bin/rexray ]; then
    # If rexray is not installed, run it in a docker container

    cat > /etc/systemd/system/rexray.service <<EOF
[Unit]
Description=Rexray container
Requires=docker.service
After=docker.service

[Service]
RemainAfterExit=yes
ExecStartPre=-/usr/bin/docker rm -f rexray
ExecStartPre=-/usr/bin/docker pull openstackmagnum/rexray:alpine
ExecStartPre=-/usr/bin/rm -f /var/run/rexray/rexray.pid
ExecStart=/usr/bin/docker run -d --name=rexray --privileged \\
--pid host \\
--net host \\
-p 7979:7979 \\
-v /run/docker/plugins:/run/docker/plugins \\
-v /var/lib/rexray:/var/lib/rexray:Z \\
-v /var/lib/libstorage:/var/lib/libstorage:rshared \\
-v /var/log/rexray:/var/log/rexray \\
-v /var/run/rexray:/var/run/rexray \\
-v /var/lib/docker:/var/lib/docker:rshared \\
-v /var/run/docker:/var/run/docker \\
-v /dev:/dev \\
-v /etc/rexray/config.yml:/etc/rexray/config.yml \\
openstackmagnum/rexray:alpine
ExecStop=/usr/bin/docker stop rexray

[Install]
WantedBy=multi-user.target
EOF
    chown root:root /etc/systemd/system/rexray.service
    chmod 644 /etc/systemd/system/rexray.service

    systemctl daemon-reload
fi

echo "starting rexray..."
systemctl enable rexray
systemctl --no-block start rexray
