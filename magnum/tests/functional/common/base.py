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

import inspect

from tempest.common import credentials_factory as common_creds
from tempest.common import dynamic_creds
from tempest_lib import base

from magnum.tests.functional.common import config
from magnum.tests.functional.common import manager


class BaseMagnumTest(base.BaseTestCase):
    """Sets up configuration required for functional tests"""

    def __init__(self, *args, **kwargs):
        super(BaseMagnumTest, self).__init__(*args, **kwargs)
        self.ic = None

    @classmethod
    def setUpClass(cls):
        super(BaseMagnumTest, cls).setUpClass()
        config.Config.setUp()

    @classmethod
    def tearDownClass(cls):
        super(BaseMagnumTest, cls).tearDownClass()

    def tearDown(self):
        super(BaseMagnumTest, self).tearDown()
        if self.ic is not None:
            self.ic.clear_creds()

    def get_clients_with_isolated_creds(self,
                                        name=None,
                                        type_of_creds="default",
                                        request_type=None):
        """Creates isolated creds.

        :param name: name, will be used for dynamic creds
        :param type_of_creds: admin, alt or default
        :param request_type: baymodel or service
        :returns: MagnumClient -- client with isolated creds.
        :returns: KeypairClient -- allows for creating of keypairs
        """
        if name is None:
            # Get name of test method
            name = inspect.stack()[1][3]
            if len(name) > 32:
                name = name[0:32]

        # Choose type of isolated creds
        self.ic = dynamic_creds.DynamicCredentialProvider(
            identity_version=config.Config.auth_version,
            name=name,
            admin_role=config.Config.admin_role,
            admin_creds=common_creds.get_configured_credentials(
                'identity_admin'))
        if "admin" == type_of_creds:
            creds = self.ic.get_admin_creds()
            manager_inst = manager.AdminManager(credentials=creds,
                                                request_type=request_type)
        elif "alt" == type_of_creds:
            creds = self.ic.get_alt_creds()
            manager_inst = manager.AltManager(credentials=creds,
                                              request_type=request_type)
        elif "default" == type_of_creds:
            creds = self.ic.get_primary_creds()
            manager_inst = manager.DefaultManager(credentials=creds,
                                                  request_type=request_type)
        else:
            creds = self.ic.self.get_credentials(type_of_creds)
            manager_inst = manager.DefaultManager(credentials=creds,
                                                  request_type=request_type)

        # create client with isolated creds
        return (manager_inst.client, manager_inst.keypairs_client)
