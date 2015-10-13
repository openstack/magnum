# SUR 2015/08/20
# Senlin replacing Heat in Magnum
# cluster_function for bay_conductor 

import argparse
import logging
import time

from magnum.common.clients import OpenStackClients as OSC
from magnum.sur.action.senlin.clusters import Cluster
from magnum.sur.action.senlin.nodes import Node
from magnum.sur.action.senlin.profiles import Profile

LOG = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

def wait_for_node_active(sc, node):
    while True:
        status = Node.node_show(sc, node)['node']['status']
        if status == 'ACTIVE':
            break
        time.sleep(1)

def create_cluster(OSC, **params):
    #LOG.info('Creating Request accepted.')
    master_profile_name = params.get('master_profile_name', 'master_profile')
    minion_profile_name = params.get('minion_profile_name', 'minion_profile')

    master_profile_spec = params.get('master_profile_spec', None)
    minion_profile_spec = params.get('minion_profile_spec', None)

    cluster_name = params.get('cluster_name', 'sur_cluster')

    master_node_name = cluster_name + '_master'
    minion_node_name = cluster_name + '_minion_'

    node_count = params.get('node_count', 1)

    # Client
    sc = OSC.senlin()

    # Create Master Profile
    #Profile.profile_create(sc, master_profile_name, 'os.heat.stack',
    #                       master_profile_spec, '1111')
    #time.sleep(1)

    # Create Master Node
    #Node.node_create(sc, master_node_name, None, master_profile_name)
    #time.sleep(5)

    # Wait for Node Active
    #wait_for_node_active(sc, master_node_name)

    # Define Minion Yaml

    # Create Minion Profile
    Profile.profile_create(sc, minion_profile_name, 'os.heat.stack',
                           minion_profile_spec, '1111')
    time.sleep(1)
    
    # Create Cluster
    #Cluster.cluster_create(sc, cluster_name, minion_profile_name)
    #time.sleep(1)

    # Master join into Cluster
    #Node.node_join(sc, master_node_name, cluster_name)
    #time.sleep(1)

    # Create Minion Node(s)
    #for i in range(node_count):
    #    Node.node_create(sc, minion_node_name + str(i), cluster_name,
    #        minion_profile_name)
    #    time.sleep(5)
    Node.node_create(sc, minion_node_name, None, minion_profile_name)
    #LOG.info('Complete') 
