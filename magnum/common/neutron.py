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

from magnum.common import clients
from magnum.common import exception

LOG = logging.getLogger(__name__)


def delete_floatingip(context, fix_port_id, cluster):
    """Deletes the floating IP associated with the fix_port_id.

    Only delete the floating IP if it's created and associated with the
    LoadBalancer type service in Kubernetes cluster.

    This method only works with the Kubernetes cluster with
    cloud-provider-openstack controller manager deployed, patched with
    this PR:
    https://github.com/kubernetes/cloud-provider-openstack/pull/433
    """
    pattern = (r'Floating IP for Kubernetes external service \w+ from cluster '
               r'%s$' % cluster.uuid)

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
            LOG.debug("Deleting floating ip %s for cluster %s", id,
                      cluster.uuid)
            n_client.delete_floatingip(id)
    except Exception as e:
        raise exception.PreDeletionFailed(cluster_uuid=cluster.uuid,
                                          msg=str(e))
