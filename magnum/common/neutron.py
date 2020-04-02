# Copyright 2019 Catalyst Cloud Ltd.
#
#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.
import re

from oslo_log import log as logging
from oslo_utils import uuidutils

from magnum.common import clients
from magnum.common import exception

LOG = logging.getLogger(__name__)


def delete_floatingip(context, fix_port_id, cluster):
    """Deletes the floating IP associated with the fix_port_id.

    Only delete the floating IP if it's created and associated with the
    the load balancers that corresponding to the services and ingresses in
    Kubernetes cluster.

    This method only works with the Kubernetes cluster with
    cloud-provider-openstack controller manager deployed.
    """
    pattern = (r'Floating IP for Kubernetes .+ from cluster %s$' %
               cluster.uuid)

    try:
        n_client = clients.OpenStackClients(context).neutron()
        fips = n_client.list_floatingips(port_id=fix_port_id)
        if len(fips["floatingips"]) == 0:
            return

        # Liberty Neutron doesn't support description field, although Liberty
        # is no longer supported, we write good code here.
        desc = fips["floatingips"][0].get("description", "")
        id = fips["floatingips"][0]["id"]

        if re.match(pattern, desc):
            LOG.info("Deleting floating ip %s for cluster %s", id,
                     cluster.uuid)
            n_client.delete_floatingip(id)
    except Exception as e:
        raise exception.PreDeletionFailed(cluster_uuid=cluster.uuid,
                                          msg=str(e))


def get_network(context, network, source, target, external):
    nets = []
    n_client = clients.OpenStackClients(context).neutron()
    filters = {source: network, 'router:external': external}
    networks = n_client.list_networks(**filters).get('networks')

    for net in networks:
        if net.get(source) == network:
            nets.append(net)

    if len(nets) == 0:
        if external:
            raise exception.ExternalNetworkNotFound(network=network)
        else:
            raise exception.FixedNetworkNotFound(network=network)

    if len(nets) > 1:
        raise exception.Conflict(
            "Multiple networks exist with same name '%s'. Please use the "
            "network ID instead." % network
        )

    return nets[0][target]


def get_external_network_id(context, network):
    if network and uuidutils.is_uuid_like(network):
        return network
    else:
        return get_network(context, network, source='name',
                           target='id', external=True)


def get_fixed_network_name(context, network):
    if network and uuidutils.is_uuid_like(network):
        return get_network(context, network, source='id',
                           target='name', external=False)
    else:
        return network


def get_subnet(context, subnet, source, target):
    nets = []
    n_client = clients.OpenStackClients(context).neutron()
    filters = {source: subnet}
    subnets = n_client.list_subnets(**filters).get('subnets', [])

    for net in subnets:
        if net.get(source) == subnet:
            nets.append(net)

    if len(nets) == 0:
        raise exception.FixedSubnetNotFound(subnet=subnet)

    if len(nets) > 1:
        raise exception.Conflict(
            "Multiple subnets exist with same name '%s'. Please use the "
            "subnet ID instead." % subnet
        )

    return nets[0][target]


def get_fixed_subnet_id(context, subnet):
    if subnet and not uuidutils.is_uuid_like(subnet):
        return get_subnet(context, subnet, source='name', target='id')
    else:
        return subnet
