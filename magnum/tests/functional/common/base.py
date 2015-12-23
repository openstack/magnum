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
from tempest_lib import base

from magnum.tests.functional.common import config
from magnum.tests.functional.common import manager


class BaseMagnumTest(base.BaseTestCase):
    """Sets up configuration required for functional tests"""

    ic_class_list = []
    ic_method_list = []

    def __init__(self, *args, **kwargs):
        super(BaseMagnumTest, self).__init__(*args, **kwargs)

    @classmethod
    def setUpClass(cls):
        super(BaseMagnumTest, cls).setUpClass()
        config.Config.setUp()

    @classmethod
    def tearDownClass(cls):
        super(BaseMagnumTest, cls).tearDownClass()
        cls.clear_credentials(clear_class_creds=True)

    def tearDown(self):
        super(BaseMagnumTest, self).tearDown()
        self.clear_credentials(clear_method_creds=True)

    @classmethod
    def clear_credentials(cls,
                          clear_class_creds=False,
                          clear_method_creds=False):
        if clear_class_creds:
            for ic in cls.ic_class_list:
                ic.clear_creds()
        if clear_method_creds:
            for ic in cls.ic_method_list:
                ic.clear_creds()

    @classmethod
    def get_credentials(cls, name=None,
                        type_of_creds="default",
                        class_cleanup=False):
        if name is None:
            # Get name of test method
            name = inspect.stack()[1][3]
            if len(name) > 32:
                name = name[0:32]

        # Choose type of isolated creds
        ic = common_creds.get_credentials_provider(
            name,
            identity_version=config.Config.auth_version
        )

        if class_cleanup:
            cls.ic_class_list.append(ic)
        else:
            cls.ic_method_list.append(ic)

        creds = None
        if "admin" == type_of_creds:
            creds = ic.get_admin_creds()
        elif "alt" == type_of_creds:
            creds = ic.get_alt_creds()
        elif "default" == type_of_creds:
            creds = ic.get_primary_creds()
        else:
            creds = ic.self.get_credentials(type_of_creds)

        _, keypairs_client = cls.get_clients(
            creds, type_of_creds, 'keypair_setup')
        try:
            keypairs_client.show_keypair(config.Config.keypair_id)
        except Exception:
            keypairs_client.create_keypair(name=config.Config.keypair_id)

        return creds

    @classmethod
    def get_clients(cls, creds, type_of_creds, request_type):
        if "admin" == type_of_creds:
            manager_inst = manager.AdminManager(credentials=creds,
                                                request_type=request_type)
        elif "alt" == type_of_creds:
            manager_inst = manager.AltManager(credentials=creds,
                                              request_type=request_type)
        elif "default" == type_of_creds:
            manager_inst = manager.DefaultManager(credentials=creds,
                                                  request_type=request_type)
        else:
            manager_inst = manager.DefaultManager(credentials=creds,
                                                  request_type=request_type)

        # create client with isolated creds
        return (manager_inst.client, manager_inst.keypairs_client)

    @classmethod
    def get_clients_with_existing_creds(cls,
                                        name=None,
                                        creds=None,
                                        type_of_creds="default",
                                        request_type=None,
                                        class_cleanup=False):
        if creds is None:
            return cls.get_clients_with_new_creds(name,
                                                  type_of_creds,
                                                  request_type,
                                                  class_cleanup)
        else:
            return cls.get_clients(creds, type_of_creds, request_type)

    @classmethod
    def get_clients_with_new_creds(cls,
                                   name=None,
                                   type_of_creds="default",
                                   request_type=None,
                                   class_cleanup=False):
        """Creates isolated creds.

        :param name: name, will be used for dynamic creds
        :param type_of_creds: admin, alt or default
        :param request_type: baymodel or service
        :returns: MagnumClient -- client with isolated creds.
        :returns: KeypairClient -- allows for creating of keypairs
        """
        creds = cls.get_credentials(name, type_of_creds, class_cleanup)
        return cls.get_clients(creds, type_of_creds, request_type)
