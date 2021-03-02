. /etc/sysconfig/heat-params

if [ "$VERIFY_CA" == "True" ]; then
    VERIFY_CA=""
else
    VERIFY_CA="-k"
fi

WC_NOTIFY_BIN=/usr/local/bin/wc-notify
WC_NOTIFY_SERVICE=/etc/systemd/system/wc-notify.service

cat > $WC_NOTIFY_BIN <<EOF
#!/bin/bash -v
until  [ "ok" = "\$(kubectl get --raw='/healthz')" ]
do
    echo "Waiting for Kubernetes API..."
    sleep 5
done
$WAIT_CURL $VERIFY_CA --data-binary '{"status": "SUCCESS"}'
EOF

cat > $WC_NOTIFY_SERVICE <<EOF
[Unit]
Description=Notify Heat
After=docker.service
Requires=docker.service
[Service]
Type=oneshot
ExecStart=$WC_NOTIFY_BIN
[Install]
WantedBy=multi-user.target
EOF

chown root:root $WC_NOTIFY_BIN
chmod 0755 $WC_NOTIFY_BIN

chown root:root $WC_NOTIFY_SERVICE
chmod 0644 $WC_NOTIFY_SERVICE

systemctl enable wc-notify
systemctl start --no-block wc-notify
