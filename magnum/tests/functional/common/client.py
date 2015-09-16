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

import six
from six.moves.urllib import parse
from tempest_lib.common import rest_client

from magnum.tests.functional.common import config
from magnum.tests.functional.common import manager
from magnum.tests.functional.common.utils import memoized


@six.add_metaclass(abc.ABCMeta)
class BaseMagnumClient(rest_client.RestClient):
    """Abstract class responsible for setting up auth provider"""

    def __init__(self):
        super(BaseMagnumClient, self).__init__(
            auth_provider=self.get_auth_provider(),
            service='container',
            region=config.Config.region
        )

    @abc.abstractmethod
    def get_auth_provider(self):
        pass


class MagnumClient(BaseMagnumClient):
    """Responsible for setting up auth provider for default user
    """

    def get_auth_provider(self):
        mgr = manager.Manager()
        return mgr.get_auth_provider(
            username=config.Config.user,
            password=config.Config.passwd,
            tenant_name=config.Config.tenant
        )


class ClientMixin(object):
    """Responsible for mapping setting up common client use cases:

    - deserializing response data to a model
    - mapping user requests to a specific client for authentication
    - generating request URLs
    """

    @classmethod
    @memoized
    def get_clients(cls):
        return {
            'default': MagnumClient(),
        }

    def __init__(self, client):
        self.client = client

    @classmethod
    def deserialize(cls, resp, body, model_type):
        return resp, model_type.from_json(body)

    @classmethod
    def as_user(cls, user):
        """Retrieves Magnum client based on user parameter

        :param user: type of user ('default')
        :returns: a class that maps to user type in get_clients dict
        """
        return cls(cls.get_clients()[user])

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
