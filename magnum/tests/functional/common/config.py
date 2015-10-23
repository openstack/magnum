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
    def set_admin_creds(cls, config):
        cls.admin_user = config.get('admin', 'user')
        cls.admin_passwd = config.get('admin', 'pass')
        cls.admin_tenant = config.get('admin', 'tenant')

    @classmethod
    def set_user_creds(cls, config):
        # normal user creds
        cls.user = config.get('auth', 'username')
        cls.passwd = config.get('auth', 'password')
        cls.tenant = config.get('auth', 'tenant_name')

    @classmethod
    def set_auth_version(cls, config):
        # auth version for client authentication
        if config.has_option('auth', 'auth_version'):
            cls.auth_version = config.get('auth', 'auth_version')
        else:
            cls.auth_version = 'v3'

    @classmethod
    def set_auth_url(cls, config):
        # auth_url for client authentication
        if cls.auth_version == 'v3':
            if not config.has_option('auth', 'auth_v3_url'):
                raise Exception('config missing auth_v3_url key')
            cls.auth_v3_url = config.get('auth', 'auth_v3_url')
        else:
            if not config.has_option('auth', 'auth_url'):
                raise Exception('config missing auth_url key')
            cls.auth_url = config.get('auth', 'auth_url')

    @classmethod
    def set_region(cls, config):
        if config.has_option('auth', 'region'):
            cls.region = config.get('auth', 'region')
        else:
            cls.region = 'RegionOne'

    @classmethod
    def set_image_id(cls, config):
        cls.image_id = config.get('magnum', 'image_id')
        if not config.has_option('magnum', 'image_id'):
            raise Exception('config missing image_id key')

    @classmethod
    def set_nic_id(cls, config):
        cls.nic_id = config.get('magnum', 'nic_id')
        if not config.has_option('magnum', 'nic_id'):
            raise Exception('config missing nic_id key')

    @classmethod
    def set_keypair_id(cls, config):
        cls.keypair_id = config.get('magnum', 'keypair_id')
        if not config.has_option('magnum', 'keypair_id'):
            raise Exception('config missing keypair_id key')

    @classmethod
    def setUp(cls):
        config = ConfigParser.RawConfigParser()
        if config.read('functional_creds.conf'):
            cls.set_admin_creds(config)
            cls.set_user_creds(config)
            cls.set_auth_version(config)
            cls.set_auth_url(config)

            # optional magnum bypass url
            cls.magnum_url = config.get('auth', 'magnum_url')

            cls.set_region(config)
            cls.set_image_id(config)
            cls.set_nic_id(config)
            cls.set_keypair_id(config)
        else:
            raise Exception('missing functional_creds.conf file')
