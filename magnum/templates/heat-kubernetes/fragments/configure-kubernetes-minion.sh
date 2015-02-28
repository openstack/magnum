#!/bin/sh

. /etc/sysconfig/heat-params

echo "configuring kubernetes (minion)"

myip=$(ip addr show eth0 |
awk '$1 == "inet" {print $2}' | cut -f1 -d/)
myip_last_octet=${myip##*.}

sed -i '
/^KUBE_ALLOW_PRIV=/ s/=.*/="--allow_privileged='"$KUBE_ALLOW_PRIV"'"/
/^KUBE_ETCD_SERVERS=/ s|=.*|="--etcd_servers=http://'"$KUBE_MASTER_IP"':4001"|
' /etc/kubernetes/config

sed -i '
/^KUBELET_ADDRESS=/ s/=.*/="--address=0.0.0.0"/
/^KUBELET_HOSTNAME=/ s/=.*/="--hostname_override='"$myip"'"/
' /etc/kubernetes/kubelet

sed -i '
/^KUBE_MASTER=/ s/=.*/="--master='"$KUBE_MASTER_IP"':8080"/
' /etc/kubernetes/apiserver

sed -i '
/^FLANNEL_ETCD=/ s|=.*|="http://'"$KUBE_MASTER_IP"':4001"|
' /etc/sysconfig/flanneld

cat >> /etc/environment <<EOF
KUBERNETES_MASTER=http://$KUBE_MASTER_IP:8080
EOF
