#cloud-boothook

setenforce `[[ "$SELINUX_MODE" == "enforcing" ]] && echo 1 || echo 0`
sed -i '
    /^SELINUX=/ s/=.*/=$SELINUX_MODE/
' /etc/selinux/config
