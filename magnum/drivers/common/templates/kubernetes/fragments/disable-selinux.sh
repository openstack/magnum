#cloud-boothook
#!/bin/sh

setenforce 0

sed -i '
    /^SELINUX=/ s/=.*/=permissive/
' /etc/selinux/config
