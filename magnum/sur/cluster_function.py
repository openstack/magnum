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

def create_cluster(OSC, Ctype):
    LOG.info('Creating Request accepted.')

    # Client
    sc = OSC.senlin()

    # Create Master Profile
    pr_master = Profile.profile_create(sc, 'SUR_HEAT_Master_Profile', 'os.heat.stack',
                '/opt/stack/magnum/magnum/sur/SURspec/heat-fedora/master.yaml', '1111')
    time.sleep(1)

    # Create Master Node
    Node.node_create(sc, 'SUR_Node_Master', None, 'SUR_HEAT_Master_Profile')
    time.sleep(1)

    # Define Minion yaml

    # Create Minion Profile
    pr_minion = Profile.profile_craete(sc, 'SUR_HEAT_Minion_Profile', 'os.heat.stack',
                '/opt/stack/magnum/magnum/sur/SURspec/heat-fedora/minion.yaml', '1111')
    time.sleep(1)
    
    # Create Cluster
    Cluster.cluster_create(sc, 'SUR_HEAT_Cluster', 'SUR_HEAT_Minion_Profile')
    time.sleep(1)

    # Master join into Cluster
    Node.node_join(sc, 'SUR_Node_Master', 'SUR_HEAT_Cluster')
    time.sleep(1)

    #LOG.info('Complete') 
