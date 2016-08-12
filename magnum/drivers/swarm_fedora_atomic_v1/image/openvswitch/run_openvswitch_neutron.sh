#!/bin/bash

/usr/share/openvswitch/scripts/ovs-ctl start --system-id=random
/usr/bin/neutron-openvswitch-agent --config-file /etc/neutron/neutron.conf  --log-file /var/log/neutron/openvswitch-agent.log
