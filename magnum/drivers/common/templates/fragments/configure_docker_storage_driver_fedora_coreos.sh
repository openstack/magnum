ssh_cmd="ssh -F /srv/magnum/.ssh/config root@localhost"

configure_storage_driver_generic() {

    cat > /etc/systemd/system/var-lib-docker.mount <<EOF
[Unit]
Description=Mount ephemeral to /var/lib/docker

[Mount]
What=/dev/vdb
Where=/var/lib/docker
Type=ext4

[Install]
WantedBy=local-fs.target
EOF


    cat > /etc/sysconfig/enable-docker-mount.sh <<EOF
#!/bin/sh
. /etc/sysconfig/heat-params
if [  -n "$DOCKER_VOLUME_SIZE" ] && [ "$DOCKER_VOLUME_SIZE" -gt 0 ]; then
    if [[ "$(blkid -o value -s TYPE /dev/vdb)" -eq 0 ]]; then
        systemctl daemon-reload
        systemctl start var-lib-docker.mount
        systemctl enable var-lib-docker.mount
    else
        mkfs -t ext4 /dev/vdb
        systemctl daemon-reload
        systemctl start var-lib-docker.mount
        systemctl enable var-lib-docker.mount
    fi
fi
EOF

    chmod +x /etc/sysconfig/enable-docker-mount.sh

    cat > /etc/systemd/system/enable-docker-mount.service <<EOF
[Unit]
Description=Mount docker volume

[Service]
Type=oneshot
EnvironmentFile=/etc/sysconfig/heat-params
ExecStart=/etc/sysconfig/enable-docker-mount.sh

[Install]
RequiredBy=multi-user.target
EOF

}

configure_devicemapper() {
    configure_storage_driver_generic
}