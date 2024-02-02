# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from oslo_log import log as logging
from tempest.lib import exceptions

from magnum.tests.functional.api.v1.models import cluster_id_model
from magnum.tests.functional.api.v1.models import cluster_model
from magnum.tests.functional.common import client
from magnum.tests.functional.common import utils


class ClusterClient(client.MagnumClient):
    """Encapsulates REST calls and maps JSON to/from models"""

    LOG = logging.getLogger(__name__)

    @classmethod
    def clusters_uri(cls, filters=None):
        """Construct clusters uri with optional filters

        :param filters: Optional k:v dict that's converted to url query
        :returns: url string
        """

        url = "/clusters"
        if filters:
            url = cls.add_filters(url, filters)
        return url

    @classmethod
    def cluster_uri(cls, cluster_id):
        """Construct cluster uri

        :param cluster_id: cluster uuid or name
        :returns: url string
        """

        return "{0}/{1}".format(cls.clusters_uri(), cluster_id)

    def list_clusters(self, filters=None, **kwargs):
        """Makes GET /clusters request and returns ClusterCollection

        Abstracts REST call to return all clusters

        :param filters: Optional k:v dict that's converted to url query
        :returns: response object and ClusterCollection object
        """

        resp, body = self.get(self.clusters_uri(filters), **kwargs)
        return self.deserialize(resp, body, cluster_model.ClusterCollection)

    def get_cluster(self, cluster_id, **kwargs):
        """Makes GET /cluster request and returns ClusterEntity

        Abstracts REST call to return a single cluster based on uuid or name

        :param cluster_id: cluster uuid or name
        :returns: response object and ClusterCollection object
        """

        resp, body = self.get(self.cluster_uri(cluster_id))
        return self.deserialize(resp, body, cluster_model.ClusterEntity)

    def post_cluster(self, model, **kwargs):
        """Makes POST /cluster request and returns ClusterIdEntity

        Abstracts REST call to create new cluster

        :param model: ClusterEntity
        :returns: response object and ClusterIdEntity object
        """

        resp, body = self.post(
            self.clusters_uri(),
            body=model.to_json(), **kwargs)
        return self.deserialize(resp, body, cluster_id_model.ClusterIdEntity)

    def patch_cluster(self, cluster_id, clusterpatch_listmodel, **kwargs):
        """Makes PATCH /cluster request and returns ClusterIdEntity

        Abstracts REST call to update cluster attributes

        :param cluster_id: UUID of cluster
        :param clusterpatch_listmodel: ClusterPatchCollection
        :returns: response object and ClusterIdEntity object
        """

        resp, body = self.patch(
            self.cluster_uri(cluster_id),
            body=clusterpatch_listmodel.to_json(), **kwargs)
        return self.deserialize(resp, body, cluster_id_model.ClusterIdEntity)

    def delete_cluster(self, cluster_id, **kwargs):
        """Makes DELETE /cluster request and returns response object

        Abstracts REST call to delete cluster based on uuid or name

        :param cluster_id: UUID or name of cluster
        :returns: response object
        """

        return self.delete(self.cluster_uri(cluster_id), **kwargs)

    def wait_for_cluster_to_delete(self, cluster_id):
        utils.wait_for_condition(
            lambda: self.does_cluster_not_exist(cluster_id), 10, 600)

    def wait_for_created_cluster(self, cluster_id, delete_on_error=True):
        try:
            utils.wait_for_condition(
                lambda: self.does_cluster_exist(cluster_id), 10, 1800)
        except Exception:
            # In error state.  Clean up the cluster id if desired
            self.LOG.error('Cluster %s entered an exception state.',
                           cluster_id)
            if delete_on_error:
                self.LOG.error('We will attempt to delete clusters now.')
                self.delete_cluster(cluster_id)
                self.wait_for_cluster_to_delete(cluster_id)
            raise

    def wait_for_final_state(self, cluster_id):
        utils.wait_for_condition(
            lambda: self.is_cluster_in_final_state(cluster_id), 10, 1800)

    def is_cluster_in_final_state(self, cluster_id):
        try:
            resp, model = self.get_cluster(cluster_id)
            if model.status in ['CREATED', 'CREATE_COMPLETE',
                                'ERROR', 'CREATE_FAILED']:
                self.LOG.info('Cluster %s succeeded.', cluster_id)
                return True
            else:
                return False
        except exceptions.NotFound:
            self.LOG.warning('Cluster %s is not found.', cluster_id)
            return False

    def does_cluster_exist(self, cluster_id):
        try:
            resp, model = self.get_cluster(cluster_id)
            if model.status in ['CREATED', 'CREATE_COMPLETE']:
                self.LOG.info('Cluster %s is created.', cluster_id)
                return True
            elif model.status in ['ERROR', 'CREATE_FAILED']:
                self.LOG.error('Cluster %s is in fail state.',
                               cluster_id)
                raise exceptions.ServerFault(
                    "Got into an error condition: %s for %s",
                    (model.status, cluster_id))
            else:
                return False
        except exceptions.NotFound:
            self.LOG.warning('Cluster %s is not found.', cluster_id)
            return False

    def does_cluster_not_exist(self, cluster_id):
        try:
            self.get_cluster(cluster_id)
        except exceptions.NotFound:
            self.LOG.warning('Cluster %s is not found.', cluster_id)
            return True
        return False
