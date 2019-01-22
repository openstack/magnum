# Copyright 2018 Catalyst Cloud Ltd.
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

from oslo_config import cfg
from oslo_log import log as logging
import re
import time

from magnum.common import clients
from magnum.common import exception
from magnum.common import neutron

LOG = logging.getLogger(__name__)
CONF = cfg.CONF


def wait_for_lb_deleted(octavia_client, deleted_lbs):
    """Wait for the loadbalancers to be deleted.

    Load balancer deletion API in Octavia is asynchronous so that the called
    needs to wait if it wants to guarantee the load balancer to be deleted.
    The timeout is necessary to avoid waiting infinitely.
    """
    timeout = CONF.cluster.pre_delete_lb_timeout
    start_time = time.time()

    while True:
        lbs = octavia_client.load_balancer_list().get("loadbalancers", [])
        lbIDs = set(
            [lb["id"]
             for lb in lbs if lb["provisioning_status"] != "DELETED"]
        )
        if not (deleted_lbs & lbIDs):
            break

        if (time.time() - timeout) > start_time:
            raise Exception("Timeout waiting for the load balancers "
                            "%s to be deleted." % deleted_lbs)

        time.sleep(1)


def delete_loadbalancers(context, cluster):
    """Delete loadbalancers for kubernetes resources.

    This method only works for the k8s cluster with
    cloud-provider-openstack manager or controller-manager patched with
    this PR:
    https://github.com/kubernetes/cloud-provider-openstack/pull/223

    The load balancers created for kubernetes services and ingresses are
    deleted.
    """
    pattern = (r'Kubernetes .+ from cluster %s$' % cluster.uuid)
    valid_status = ["ACTIVE", "ERROR", "PENDING_DELETE", "DELETED"]

    try:
        o_client = clients.OpenStackClients(context).octavia()
        lbs = o_client.load_balancer_list().get("loadbalancers", [])

        candidates = set()
        invalids = set()
        for lb in lbs:
            if re.match(pattern, lb["description"]):
                if lb["provisioning_status"] not in valid_status:
                    invalids.add(lb["id"])
                    continue
                if lb["provisioning_status"] in ["ACTIVE", "ERROR"]:
                    # Delete VIP floating ip if needed.
                    neutron.delete_floatingip(context, lb["vip_port_id"],
                                              cluster)

                    LOG.debug("Deleting load balancer %s for cluster %s",
                              lb["id"], cluster.uuid)
                    o_client.load_balancer_delete(lb["id"], cascade=True)
                candidates.add(lb["id"])

        if invalids:
            raise Exception("Cannot delete load balancers %s in transitional "
                            "status." % invalids)
        if not candidates:
            return

        wait_for_lb_deleted(o_client, candidates)
    except Exception as e:
        raise exception.PreDeletionFailed(cluster_uuid=cluster.uuid,
                                          msg=str(e))
