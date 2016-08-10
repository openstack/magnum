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

from magnum.tests.functional.api.v1.models import cluster_template_model
from magnum.tests.functional.common import client


class ClusterTemplateClient(client.MagnumClient):
    """Encapsulates REST calls and maps JSON to/from models"""

    @classmethod
    def cluster_templates_uri(cls, filters=None):
        """Construct clustertemplates uri with optional filters

        :param filters: Optional k:v dict that's converted to url query
        :returns: url string
        """

        url = "/clustertemplates"
        if filters:
            url = cls.add_filters(url, filters)
        return url

    @classmethod
    def cluster_template_uri(cls, cluster_template_id):
        """Construct cluster_template uri

        :param cluster_template_id: cluster_template uuid or name
        :returns: url string
        """

        return "{0}/{1}".format(cls.cluster_templates_uri(),
                                cluster_template_id)

    def list_cluster_templates(self, filters=None, **kwargs):
        """Makes GET /clustertemplates request

        Abstracts REST call to return all clustertemplates

        :param filters: Optional k:v dict that's converted to url query
        :returns: response object and ClusterTemplateCollection object
        """

        resp, body = self.get(self.cluster_templates_uri(filters), **kwargs)
        collection = cluster_template_model.ClusterTemplateCollection
        return self.deserialize(resp, body, collection)

    def get_cluster_template(self, cluster_template_id, **kwargs):
        """Makes GET /clustertemplate request and returns ClusterTemplateEntity

        Abstracts REST call to return a single clustertempalte based on uuid
        or name

        :param cluster_template_id: clustertempalte uuid or name
        :returns: response object and ClusterTemplateCollection object
        """

        resp, body = self.get(self.cluster_template_uri(cluster_template_id))
        return self.deserialize(resp, body,
                                cluster_template_model.ClusterTemplateEntity)

    def post_cluster_template(self, model, **kwargs):
        """Makes POST /clustertemplate request

        Abstracts REST call to create new clustertemplate

        :param model: ClusterTemplateEntity
        :returns: response object and ClusterTemplateEntity object
        """

        resp, body = self.post(
            self.cluster_templates_uri(),
            body=model.to_json(), **kwargs)
        entity = cluster_template_model.ClusterTemplateEntity
        return self.deserialize(resp, body, entity)

    def patch_cluster_template(self, cluster_template_id,
                               cluster_templatepatch_listmodel, **kwargs):
        """Makes PATCH /clustertemplate and returns ClusterTemplateEntity

        Abstracts REST call to update clustertemplate attributes

        :param cluster_template_id: UUID of clustertemplate
        :param cluster_templatepatch_listmodel: ClusterTemplatePatchCollection
        :returns: response object and ClusterTemplateEntity object
        """

        resp, body = self.patch(
            self.cluster_template_uri(cluster_template_id),
            body=cluster_templatepatch_listmodel.to_json(), **kwargs)
        return self.deserialize(resp, body,
                                cluster_template_model.ClusterTemplateEntity)

    def delete_cluster_template(self, cluster_template_id, **kwargs):
        """Makes DELETE /clustertemplate request and returns response object

        Abstracts REST call to delete clustertemplate based on uuid or name

        :param cluster_template_id: UUID or name of clustertemplate
        :returns: response object
        """

        return self.delete(self.cluster_template_uri(cluster_template_id),
                           **kwargs)
