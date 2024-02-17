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

import abc
from urllib import parse

from tempest.lib.common import rest_client

from magnum.tests.functional.common import config


class MagnumClient(rest_client.RestClient, metaclass=abc.ABCMeta):
    """Abstract class responsible for setting up auth provider"""

    def __init__(self, auth_provider):
        super(MagnumClient, self).__init__(
            auth_provider=auth_provider,
            service='container-infra',
            region=config.Config.region,
            disable_ssl_certificate_validation=True
        )

    @classmethod
    def deserialize(cls, resp, body, model_type):
        return resp, model_type.from_json(body)

    @property
    def tenant_id(self):
        return self.client.tenant_id

    @classmethod
    def add_filters(cls, url, filters):
        """add_filters adds dict values (filters) to url as query parameters

        :param url: base URL for the request
        :param filters: dict with var:val pairs to add as parameters to URL
        :returns: url string
        """
        return url + "?" + parse(filters)
