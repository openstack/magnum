#!/bin/bash
#================
# FILE          : image.sh
#----------------
# PROJECT       : openSUSE KIWI Image System
# COPYRIGHT     : (c) 2006 SUSE LINUX Products GmbH. All rights reserved
#               :
# AUTHOR        : Marcus Schaefer <ms@suse.de>
#               :
# BELONGS TO    : Operating System images
#               :
# DESCRIPTION   : configuration script for SUSE based
#               : operating systems
#               :
#               :
# STATUS        : BETA
#----------------

test -f /.kconfig && . /.kconfig
test -f /.profile && . /.profile

if [[ "${kiwi_iname}" = *"OpenStack"* ]]; then
  # disable jeos-firstboot service
  # We need to install it because it provides files required in the
  # overlay for the image. However, the service itself is something that
  # requires interaction on boot, which is not good for OpenStack, and the
  # interaction actually doesn't bring any benefit in OpenStack.
  systemctl mask jeos-firstboot.service

  # enable cloud-init services
  suseInsertService cloud-init-local
  suseInsertService cloud-init
  suseInsertService cloud-config
  suseInsertService cloud-final

  echo '*** adjusting cloud.cfg for openstack'
  sed -i -e '/mount_default_fields/{adatasource_list: [ NoCloud, OpenStack, None ]
  }' /etc/cloud/cloud.cfg
fi
