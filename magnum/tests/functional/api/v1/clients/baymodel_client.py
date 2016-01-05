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

from magnum.tests.functional.api.v1.models import baymodel_model
from magnum.tests.functional.common import client


class BayModelClient(client.MagnumClient):
    """Encapsulates REST calls and maps JSON to/from models"""

    @classmethod
    def baymodels_uri(cls, filters=None):
        """Construct baymodels uri with optional filters

        :param filters: Optional k:v dict that's converted to url query
        :returns: url string
        """

        url = "/baymodels"
        if filters:
            url = cls.add_filters(url, filters)
        return url

    @classmethod
    def baymodel_uri(cls, baymodel_id):
        """Construct baymodel uri

        :param baymodel_id: baymodel uuid or name
        :returns: url string
        """

        return "{0}/{1}".format(cls.baymodels_uri(), baymodel_id)

    def list_baymodels(self, filters=None, **kwargs):
        """Makes GET /baymodels request and returns BayModelCollection

        Abstracts REST call to return all baymodels

        :param filters: Optional k:v dict that's converted to url query
        :returns: response object and BayModelCollection object
        """

        resp, body = self.get(self.baymodels_uri(filters), **kwargs)
        return self.deserialize(resp, body, baymodel_model.BayModelCollection)

    def get_baymodel(self, baymodel_id, **kwargs):
        """Makes GET /baymodel request and returns BayModelEntity

        Abstracts REST call to return a single baymodel based on uuid or name

        :param baymodel_id: baymodel uuid or name
        :returns: response object and BayModelCollection object
        """

        resp, body = self.get(self.baymodel_uri(baymodel_id))
        return self.deserialize(resp, body, baymodel_model.BayModelEntity)

    def post_baymodel(self, model, **kwargs):
        """Makes POST /baymodel request and returns BayModelEntity

        Abstracts REST call to create new baymodel

        :param model: BayModelEntity
        :returns: response object and BayModelEntity object
        """

        resp, body = self.post(
            self.baymodels_uri(),
            body=model.to_json(), **kwargs)
        return self.deserialize(resp, body, baymodel_model.BayModelEntity)

    def patch_baymodel(self, baymodel_id, baymodelpatch_listmodel, **kwargs):
        """Makes PATCH /baymodel request and returns BayModelEntity

        Abstracts REST call to update baymodel attributes

        :param baymodel_id: UUID of baymodel
        :param baymodelpatch_listmodel: BayModelPatchCollection
        :returns: response object and BayModelEntity object
        """

        resp, body = self.patch(
            self.baymodel_uri(baymodel_id),
            body=baymodelpatch_listmodel.to_json(), **kwargs)
        return self.deserialize(resp, body, baymodel_model.BayModelEntity)

    def delete_baymodel(self, baymodel_id, **kwargs):
        """Makes DELETE /baymodel request and returns response object

        Abstracts REST call to delete baymodel based on uuid or name

        :param baymodel_id: UUID or name of baymodel
        :returns: response object
        """

        return self.delete(self.baymodel_uri(baymodel_id), **kwargs)
