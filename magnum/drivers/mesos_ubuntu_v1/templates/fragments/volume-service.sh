#!/bin/sh
. /etc/sysconfig/heat-params

# Judge whether to install the rexray driver
if [ "$VOLUME_DRIVER" != "rexray" ]; then
    exit 0
fi

curl -sSL https://dl.bintray.com/emccode/rexray/install | sh -

CLOUD_CONFIG=/etc/rexray/config.yml
CLOUD=/etc/rexray

if [ ! -d ${CLOUD_CONFIG} -o ! -d ${CLOUD} ]; then
    mkdir  -p $CLOUD
fi

if [ ${AUTH_URL##*/}=="v3" ]; then
    extra_configs="domainName:           $DOMAIN_NAME"
fi

cat > $CLOUD_CONFIG <<EOF
rexray:
  storageDrivers:
  - openstack
  volume:
    mount:
      preempt: $REXRAY_PREEMPT
openstack:
  authUrl:              $AUTH_URL
  username:             $USERNAME
  password:             $PASSWORD
  tenantName:           $TENANT_NAME
  regionName:           $REGION_NAME
  availabilityZoneName: nova
  $extra_configs
EOF

service rexray start
