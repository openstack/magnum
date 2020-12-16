FROM fedora:23
MAINTAINER Ton Ngo "ton@us.ibm.com"
WORKDIR /
RUN dnf -y install openvswitch \
        openstack-neutron-ml2 \
        openstack-neutron-openvswitch \
        bridge-utils \
        git \
    && dnf clean all
RUN cd /opt \
    && git clone https://git.openstack.org/openstack/neutron \
    && cp neutron/etc/policy.yaml /etc/neutron/. \
    && rm -rf neutron \
    && dnf -y remove git
VOLUME /var/run/openvswitch
ADD run_openvswitch_neutron.sh /usr/bin/run_openvswitch_neutron.sh

CMD ["/usr/bin/run_openvswitch_neutron.sh"]
