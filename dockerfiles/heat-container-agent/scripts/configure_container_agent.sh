#!/bin/bash
set -eux

# initial /etc/os-collect-config.conf
if [ ! -f /etc/os-collect-config.conf ] ; then
    cat <<EOF >/etc/os-collect-config.conf
[DEFAULT]
command = os-refresh-config
EOF
chmod 600 /etc/os-collect-config.conf
fi

# os-refresh-config scripts directory
# This moves to /usr/libexec/os-refresh-config in later releases
# Be sure to have this dir mounted and created by config.json and tmpfiles
orc_scripts=/opt/stack/os-config-refresh
for d in pre-configure.d configure.d migration.d post-configure.d; do
    if [ ! -d $orc_scripts/$d ] ; then
        install -m 0755 -o root -g root -d $orc_scripts/$d
    fi
done

# os-refresh-config script for running os-apply-config
if [ ! -f $orc_scripts/configure.d/20-os-apply-config ] ; then
    cat <<EOF >$orc_scripts/configure.d/20-os-apply-config
#!/bin/bash
set -ue

exec os-apply-config
EOF
fi

if [ ! -f $orc_scripts/configure.d/55-heat-config ] ; then
    chmod 700 $orc_scripts/configure.d/20-os-apply-config
    cp /opt/heat-container-agent/scripts/55-heat-config $orc_scripts/configure.d/55-heat-config
    chmod 700 $orc_scripts/configure.d/55-heat-config
fi

if [ ! -f $orc_scripts/configure.d/50-heat-config-docker-compose ] ; then
    cp /opt/heat-container-agent/scripts/50-heat-config-docker-compose $orc_scripts/configure.d/50-heat-config-docker-compose
    chmod 700 $orc_scripts/configure.d/50-heat-config-docker-compose
fi

if [ ! -f /var/lib/heat-config/hooks/atomic ] && [ ! -f /var/lib/heat-config/hooks/docker-compose ] && [ ! -f /var/lib/heat-config/hooks/script ] ; then
    mkdir -p /var/lib/heat-config/hooks
    cp /opt/heat-container-agent/hooks/* /var/lib/heat-config/hooks/
    chmod 755 /var/lib/heat-config/hooks/atomic
    chmod 755 /var/lib/heat-config/hooks/docker-compose
    chmod 755 /var/lib/heat-config/hooks/script
fi
