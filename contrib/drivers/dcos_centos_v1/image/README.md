=============
centos-dcos
=============

This directory contains `[diskimage-builder](https://github.com/openstack/diskimage-builder)`
elements to build an centos image which contains dcos.


Pre-requisites to run diskimage-builder
---------------------------------------

For diskimage-builder to work, following packages need to be
present:

* kpartx
* qemu-utils
* curl
* xfsprogs
* yum
* yum-utils
* git

For Debian/Ubuntu systems, use::

    apt-get install kpartx qemu-utils curl xfsprogs yum yum-utils git

For CentOS and Fedora < 22, use::

    yum install kpartx qemu-utils curl xfsprogs yum yum-utils git

For Fedora >= 22, use::

    dnf install kpartx @virtualization curl xfsprogs yum yum-utils git


How to generate Centos image with DC/OS 1.8.x
---------------------------------------------

1. Download and export element path

   git clone https://git.openstack.org/openstack/magnum
   git clone https://git.openstack.org/openstack/diskimage-builder.git
   git clone https://git.openstack.org/openstack/dib-utils.git
   git clone https://git.openstack.org/openstack/tripleo-image-elements.git
   git clone https://git.openstack.org/openstack/heat-templates.git

   export PATH="${PWD}/diskimage-builder/bin:$PATH"
   export PATH="${PWD}/dib-utils/bin:$PATH"
   export ELEMENTS_PATH=magnum/contrib/drivers/dcos_centos_v1/image
   export ELEMENTS_PATH=${ELEMENTS_PATH}:diskimage-builder/elements
   export ELEMENTS_PATH=${ELEMENTS_PATH}:tripleo-image-elements/elements:heat-templates/hot/software-config/elements

2. Export environment path of the url to download dcos_generate_config.sh
   This default download url is for DC/OS 1.8.4

   export DCOS_GENERATE_CONFIG_SRC=https://downloads.dcos.io/dcos/stable/commit/e64024af95b62c632c90b9063ed06296fcf38ea5/dcos_generate_config.sh

   Or specify local file path

   export DCOS_GENERATE_CONFIG_SRC=`pwd`/dcos_generate_config.sh

3. Set file system type to `xfs`
   Only XFS is currently supported for overlay.
   See https://dcos.io/docs/1.8/administration/installing/custom/system-requirements/install-docker-centos/#recommendations

   export FS_TYPE=xfs

4. Create image

   disk-image-create \
   centos7 vm docker dcos selinux-permissive \
   os-collect-config os-refresh-config os-apply-config \
   heat-config heat-config-script \
   -o centos-7-dcos.qcow2

5. (Optional) Create user image for bare metal node
   Create with elements dhcp-all-interfaces and devuser

   export DIB_DEV_USER_USERNAME=centos
   export DIB_DEV_USER_PWDLESS_SUDO=YES

   disk-image-create \
   centos7 vm docker dcos selinux-permissive dhcp-all-interfaces devuser \
   os-collect-config os-refresh-config os-apply-config \
   heat-config heat-config-script \
   -o centos-7-dcos-bm.qcow2
