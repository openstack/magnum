How to build a centos image which contains DC/OS 1.8.x
======================================================

Here is the advanced DC/OS 1.8 installation guide.

See [Advanced DC/OS Installation Guide]
(https://dcos.io/docs/1.8/administration/installing/custom/advanced/)
See [Install Docker on CentOS]
(https://dcos.io/docs/1.8/administration/installing/custom/system-requirements/install-docker-centos/)
See [Adding agent nodes]
(https://dcos.io/docs/1.8/administration/installing/custom/add-a-node/)

Create a centos image using DIB following the steps outlined in DC/OS installation guide.

1. Install and configure docker in chroot.
2. Install system requirements in chroot.
3. Download `dcos_generate_config.sh` outside chroot.
   This file will be used to run `dcos_generate_config.sh --genconf` to generate
   config files on the node during magnum cluster creation.
4. Some configuration changes are required for DC/OS, i.e disabling the firewalld
   and adding the group named nogroup.
   See comments in the script file.

Use the centos image to build a DC/OS cluster.
Command:
   `magnum cluster-template-create`
   `magnum cluster-create`

After all the instances with centos image are created.
1. Pass parameters to config.yaml with magnum cluster template properties.
2. Run `dcos_generate_config.sh --genconf` to generate config files.
3. Run `dcos_install.sh master` on master node and `dcos_install.sh slave` on slave node.

If we want to scale the DC/OS cluster.
Command:
   `magnum cluster-update`

The same steps as cluster creation.
1. Create new instances, generate config files on them and install.
2. Or delete those agent nodes where containers are not running.


How to use magnum dcos coe
===============================================

We are assuming that magnum has been installed and the magnum path is `/opt/stack/magnum`.

1. Copy dcos magnum coe source code
$ mv -r /opt/stack/magnum/contrib/drivers/dcos_centos_v1 /opt/stack/magnum/magnum/drivers/
$ mv /opt/stack/magnum/contrib/drivers/common/dcos_* /opt/stack/magnum/magnum/drivers/common/
$ cd /opt/stack/magnum
$ sudo python setup.py install

2. Add driver in setup.cfg
dcos_centos_v1 = magnum.drivers.dcos_centos_v1.driver:Driver

3. Restart your magnum services.

4. Prepare centos image with elements dcos and docker installed
   See how to build a centos image in /opt/stack/magnum/magnum/drivers/dcos_centos_v1/image/README.md

5. Create glance image
$ openstack image create centos-7-dcos.qcow2 \
          --public \
          --disk-format=qcow2 \
          --container-format=bare \
          --property os_distro=centos \
          --file=centos-7-dcos.qcow2

6. Create magnum cluster template
   Configure DC/OS cluster with --labels
   See https://dcos.io/docs/1.8/administration/installing/custom/configuration-parameters/
$ magnum cluster-template-create --name dcos-cluster-template \
          --image-id centos-7-dcos.qcow2 \
          --keypair-id testkey \
          --external-network-id public \
          --dns-nameserver 8.8.8.8 \
          --flavor-id m1.medium \
          --labels oauth_enabled=false \
          --coe dcos

   Here is an example to specify the overlay network in DC/OS,
   'dcos_overlay_network' should be json string format.
$ magnum cluster-template-create --name dcos-cluster-template \
          --image-id centos-7-dcos.qcow2 \
          --keypair-id testkey \
          --external-network-id public \
          --dns-nameserver 8.8.8.8 \
          --flavor-id m1.medium \
          --labels oauth_enabled=false \
          --labels dcos_overlay_enable='true' \
          --labels dcos_overlay_config_attempts='6' \
          --labels dcos_overlay_mtu='9001' \
          --labels dcos_overlay_network='{"vtep_subnet": "44.128.0.0/20",\
          "vtep_mac_oui": "70:B3:D5:00:00:00","overlays":\
          [{"name": "dcos","subnet": "9.0.0.0/8","prefix": 26}]}' \
          --coe dcos

7. Create magnum cluster
$ magnum cluster-create --name dcos-cluster --cluster-template dcos-cluster-template --node-count 1

8. You need to wait for a while after magnum cluster creation completed to make
   DC/OS web interface accessible.
