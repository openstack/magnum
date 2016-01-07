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

from magnum.tests.functional.api.v1.models import magnum_service_model
from magnum.tests.functional.common import client


class MagnumServiceClient(client.MagnumClient):
    """Encapsulates REST calls and maps JSON to/from models"""

    @classmethod
    def magnum_service_uri(cls, filters=None):
        """Construct magnum services uri with optional filters

        :param filters: Optional k:v dict that's converted to url query
        :returns: url string
        """

        url = "/mservices"
        if filters:
            url = cls.add_filters(url, filters)
        return url

    def magnum_service_list(self, filters=None, **kwargs):
        """Makes GET /mservices request and returns MagnumServiceCollection

        Abstracts REST call to return all magnum services.

        :param filters: Optional k:v dict that's converted to url query
        :returns: response object and MagnumServiceCollection object
        """

        resp, body = self.get(self.magnum_service_uri(filters), **kwargs)
        return self.deserialize(resp, body,
                                magnum_service_model.MagnumServiceCollection)
