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
        fips = list(n_client.ips(port_id=fix_port_id))
        if len(fips) == 0:
            return

        desc = fips[0].description or ""
        fip_id = fips[0].id

        if re.match(pattern, desc):
            LOG.info("Deleting floating ip %s for cluster %s", fip_id,
                     cluster.uuid)
            n_client.delete_ip(fip_id)
    except Exception as e:
        raise exception.PreDeletionFailed(cluster_uuid=cluster.uuid,
                                          msg=str(e))


def get_network(context, network, source, target, external):
    nets = []
    n_client = clients.OpenStackClients(context).neutron()
    filters = {source: network, 'is_router_external': external}
    networks = list(n_client.networks(**filters))

    for net in networks:
        if getattr(net, source) == network:
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

    return getattr(nets[0], target)


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
    subnets = list(n_client.subnets(**filters))

    for net in subnets:
        if getattr(net, source) == subnet:
            nets.append(net)

    if len(nets) == 0:
        raise exception.FixedSubnetNotFound(subnet=subnet)

    if len(nets) > 1:
        raise exception.Conflict(
            "Multiple subnets exist with same name '%s'. Please use the "
            "subnet ID instead." % subnet
        )

    return getattr(nets[0], target)


def get_fixed_subnet_id(context, subnet):
    if subnet and not uuidutils.is_uuid_like(subnet):
        return get_subnet(context, subnet, source='name', target='id')
    else:
        return subnet
