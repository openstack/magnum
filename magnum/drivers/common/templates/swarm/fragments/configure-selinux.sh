#cloud-boothook
#!/bin/sh

# files in /usr/local/bin should be labeled bin_t
# however on Atomic /usr/local is a symlink to /var/usrlocal
# so the default Fedora policy doesn't work
echo '/var/usrlocal/(.*/)?bin(/.*)?    system_u:object_r:bin_t:s0' > /etc/selinux/targeted/contexts/files/file_contexts.local
restorecon -R /usr/local/bin

# disable selinux until cloud-init is over
# enabled again in enable-services.sh
setenforce 0
