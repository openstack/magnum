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

import ConfigParser


class Config(object):

    """Parses configuration to attributes required for auth and test data"""

    @classmethod
    def setUp(cls):
        config = ConfigParser.RawConfigParser()
        if config.read('functional_creds.conf'):
            # admin creds
            cls.admin_user = config.get('admin', 'user')
            cls.admin_passwd = config.get('admin', 'pass')
            cls.admin_tenant = config.get('admin', 'tenant')

            # normal user creds
            cls.user = config.get('auth', 'username')
            cls.passwd = config.get('auth', 'password')
            cls.tenant = config.get('auth', 'tenant_name')

            # auth version for client authentication
            if config.has_option('auth', 'auth_version'):
                cls.auth_version = config.get('auth', 'auth_version')
            else:
                cls.auth_version = 'v3'

            # auth_url for client authentication
            if cls.auth_version == 'v3':
                if not config.has_option('auth', 'auth_v3_url'):
                    raise Exception('config missing auth_v3_url key')
                cls.auth_v3_url = config.get('auth', 'auth_v3_url')
            else:
                if not config.has_option('auth', 'auth_url'):
                    raise Exception('config missing auth_url key')
                cls.auth_url = config.get('auth', 'auth_url')

            # optional magnum bypass url
            cls.magnum_url = config.get('auth', 'magnum_url')

            if config.has_option('auth', 'region'):
                cls.region = config.get('auth', 'region')
            else:
                cls.region = 'RegionOne'

            # magnum functional test variables
            cls.image_id = config.get('magnum', 'image_id')
            if not config.has_option('magnum', 'image_id'):
                raise Exception('config missing image_id key')

            cls.nic_id = config.get('magnum', 'nic_id')
            if not config.has_option('magnum', 'nic_id'):
                raise Exception('config missing nic_id key')

            cls.keypair_id = config.get('magnum', 'keypair_id')
            if not config.has_option('magnum', 'keypair_id'):
                raise Exception('config missing keypair_id key')
        else:
            raise Exception('missing functional_creds.conf file')
