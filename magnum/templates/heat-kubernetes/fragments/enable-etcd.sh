#!/bin/sh

echo "starting etcd"
systemctl enable etcd
systemctl --no-block start etcd
