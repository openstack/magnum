# SUR 2015/08/20
# Senlin replacing Heat in Magnum
# cluster_function for bay_conductor 

import argparse
import logging
import time

from magnum.common.clients import OpenStackClients as OSC
from magnum.sur.action.clusters import Cluster
from magnum.sur.action.nodes import Node
from magnum.sur.action.profiles import Profile

LOG = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

def create_cluster(OSC, Ctype):
    LOG.info('Creating Request accepted.')

    # Client
    sc = OSC.senlin()

    # Create Profile
    pr_master = Profile.profile_create(sc, 'SUR_HEAT_Master_Profile', 'os.heat.stack',
                '/opt/stack/magnum/magnum/sur/SURspec/heat-fedora/?', '1111')

    pr_minion = Profile.profile_create(sc, 'SUR_HEAT_Minion_Profile', 'os.heat.stack',
                '/opt/stack/magnum/magnum/sur/SURspec/heat-fedora/?', '1111')

    pr_cluster = Profile.profile_create(sc, 'SUR_HEAT_Cluster_Profile', 'os.heat.stack',
                 '/opt/stack/magnum/magnum/sur/SURspec/heat-fedora/?', '1111')

    time.sleep(1)
    LOG.info(pr_master)
    LOG.info(pr_minion)
    LOG.info(pr_cluster)
    
    # Create Cluster
    cr_cluster = Cluster.cluster_create(sc, 'SUR_HEAT_Cluster', 'SUR_HEAT_Cluster_Profile')
    time.sleep(1)
    LOG.info(cr_cluster)

    # Create Nodes
    #nr_master = Node.node_create(sc, 'SUR_Node_Master', 'SUR_Master_Cluster',
    #                             'SUR_Master_Profile')
    #time.sleep(1)
    #LOG.info(nr_master)

    #nr_minion = Node.node_create(sc, 'SUR_Node_Minion', 'SUR_Minion_Cluster',
    #                             'SUR_Minion_Profile')
    #time.sleep(1)
    #LOG.info(nr_minion)

    #LOG.info('Complete')
    
