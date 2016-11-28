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

from magnum.tests.functional.api.v1.models import cert_model
from magnum.tests.functional.common import client


class CertClient(client.MagnumClient):
    """Encapsulates REST calls and maps JSON to/from models"""

    url = "/certificates"

    @classmethod
    def cert_uri(cls, cluster_id):
        """Construct cluster uri

        :param cluster_id: cluster uuid or name
        :returns: url string
        """

        return "{0}/{1}".format(cls.url, cluster_id)

    def get_cert(self, cluster_id, **kwargs):
        """Makes GET /certificates/cluster_id request and returns CertEntity

        Abstracts REST call to return a single cert based on uuid or name

        :param cluster_id: cluster uuid or name
        :returns: response object and ClusterCollection object
        """

        resp, body = self.get(self.cert_uri(cluster_id), **kwargs)
        return self.deserialize(resp, body, cert_model.CertEntity)

    def post_cert(self, model, **kwargs):
        """Makes POST /certificates request and returns CertEntity

        Abstracts REST call to sign new certificate

        :param model: CertEntity
        :returns: response object and CertEntity object
        """

        resp, body = self.post(
            CertClient.url,
            body=model.to_json(), **kwargs)
        return self.deserialize(resp, body, cert_model.CertEntity)
