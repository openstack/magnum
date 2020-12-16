===================
Neutron Openvswitch
===================

This Dockerfile creates a Docker image based on Fedora 23 that runs
Openvswitch and the Neutron L2 agent for Openvswitch.  This container
image is used by Magnum when a Swarm cluster is deployed with the
attribute::

  --network-driver=kuryr

Magnum deploys this container on each Swarm node along with the
Kuryr container to support Docker advanced networking based on
the `Container Networking Model
<https://github.com/docker/libnetwork/blob/master/docs/design.md>`_.

To build the image, run this command in the same directory as the
Dockerfile::

  docker build -t openstackmagnum/fedora23-neutron-ovs:testing .

This image is available on Docker Hub as::

  openstackmagnum/fedora23-neutron-ovs:testing

To update the image with a new build::

  docker push openstackmagnum/fedora23-neutron-ovs:testing

The 'testing' tag may be replaced with 'latest' or other tag as
needed.

This image is intended to run on the Fedora Atomic public image which
by default does not have these packages installed.  The common
practice for Atomic OS is to run new packages in containers rather
than installing them in the OS.

For the Neutron agent, you will need to provide 3 files at these
locations:

- /etc/neutron/neutron.conf
- /etc/neutron/policy.yaml
- /etc/neutron/plugins/ml2/ml2_conf.ini

These files are typically installed in the same locations on the
Neutron controller node.  The policy.yaml file is copied into the
Docker image because it is fairly static and does not require
customization for the cluster.  If it is changed in the Neutron master
repo, you just need to rebuild the Docker image to update the file.
Magnum will create the other 2 files on each cluster node in the
directory /etc/kuryr and map them to the proper directories in
the container using the Docker -v option.

Since Openvswitch needs to operate on the host network name space,
the Docker container will need the -net=host option.
The /var/run/openvswitch directory is also mapped to the cluster node
so that the Kuryr container can talk to openvswitch.
To run the image from Fedora Atomic::

  docker run --net=host \
             --cap-add=NET_ADMIN \
             --privileged=true \
             -v /var/run/openvswitch:/var/run/openvswitch \
             -v /lib/modules:/lib/modules:ro \
             -v /etc/kuryr/neutron.conf:/etc/neutron/neutron.conf \
             -v /etc/kuryr/ml2_conf.ini:/etc/neutron/plugins/ml2/ml2_conf.ini \
             --name openvswitch-agent \
             openstackmagnum/fedora23-neutron-ovs:testing
