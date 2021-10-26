# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from oslo_log import log as logging

from magnum.drivers.common import driver
from magnum.objects import fields

LOG = logging.getLogger(__name__)


class Driver(driver.Driver):

    @property
    def provides(self):
        return [
            {'server_type': 'vm',
             # NOTE(johngarbutt) we could support any cluster api
             # supported image, but lets start with ubuntu for now.
             # TODO(johngarbutt) os list should probably come from config?
             'os': 'ubuntu',
             'coe': 'kubernetes'},
        ]

    def update_cluster_status(self, context, cluster):
        # Fetch the current state of Cluster,
        # but note the race condition that it might not be created yet
        previous_state = self.cluster.status
        if previous_state == fields.ClusterStatus.CREATE_IN_PROGRESS:
            LOG.info("Fail all create attempts for now %s", cluster.uuid)
            self.cluster.status = fields.ClusterStatus.CREATE_FAILED
            self.cluster.status_reason = "not implemented"
            self.cluster.save()
        if previous_state == fields.ClusterStatus.DELETE_IN_PROGRESS:
            LOG.info("We fake that the delete was complete %s", cluster.uuid)
            self.cluster.status = fields.ClusterStatus.DELETE_COMPLETE
            self.cluster.save()
        # NOTE(johngarbutt) default to no update to the cluster state

    def create_cluster(self, context, cluster, cluster_create_timeout):
        # TODO(johngarbutt) make create do something real
        LOG.info("Starting to create cluster %s", cluster.uuid)

    def update_cluster(self, context, cluster, scale_manager=None,
                       rollback=False):
        raise Exception("not implemented update yet!")

    def delete_cluster(self, context, cluster):
        # TODO(johngarbutt) make the delete do something real
        LOG.info("Starting to delete cluster %s", cluster.uuid)

    def resize_cluster(self, context, cluster, resize_manager, node_count,
                       nodes_to_remove, nodegroup=None):
        raise Exception("don't support removing nodes this way yet")

    def upgrade_cluster(self, context, cluster, cluster_template,
                        max_batch_size, nodegroup, scale_manager=None,
                        rollback=False):
        raise Exception("don't support upgrade yet")

    def create_nodegroup(self, context, cluster, nodegroup):
        raise Exception("we don't support node groups yet")

    def update_nodegroup(self, context, cluster, nodegroup):
        raise Exception("we don't support node groups yet")

    def delete_nodegroup(self, context, cluster, nodegroup):
        raise Exception("we don't support node groups yet")

    def create_federation(self, context, federation):
        return NotImplementedError("Will not implement 'create_federation'")

    def update_federation(self, context, federation):
        return NotImplementedError("Will no implement 'update_federation'")

    def delete_federation(self, context, federation):
        return NotImplementedError("Will not implement 'delete_federation'")
