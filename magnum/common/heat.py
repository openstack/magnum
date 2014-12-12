# Copyright 2014 NEC Corporation.  All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from heatclient import client as heatclient
from oslo.config import cfg

from magnum.common import exception
from magnum.common import keystone
from magnum.openstack.common._i18n import _
from magnum.openstack.common import log as logging


LOG = logging.getLogger(__name__)


heat_client_opts = [
    cfg.StrOpt('endpoint_type',
               default='publicURL',
               help=_(
                   'Type of endpoint in Identity service catalog to use '
                   'for communication with the OpenStack service.')),
    cfg.StrOpt('ca_file',
               help=_('Optional CA cert file to use in SSL connections.')),
    cfg.StrOpt('cert_file',
               help=_('Optional PEM-formatted certificate chain file.')),
    cfg.StrOpt('key_file',
               help=_('Optional PEM-formatted file that contains the '
                      'private key.')),
    cfg.BoolOpt('insecure',
                default=False,
                help=_("If set, then the server's certificate will not "
                       "be verified."))]

cfg.CONF.register_opts(heat_client_opts, group='heat_client')


cfg.CONF.import_opt('auth_uri', 'keystonemiddleware.auth_token',
                    group='keystone_authtoken')
cfg.CONF.import_opt('auth_version', 'keystonemiddleware.auth_token',
                    group='keystone_authtoken')


@exception.wrap_keystone_exception
def get_client(context):
    endpoint_type = cfg.CONF.heat_client.endpoint_type
    auth_url = cfg.CONF.keystone_authtoken.auth_uri,
    auth_version = cfg.CONF.keystone_authtoken.auth_version
    auth_url = keystone.get_keystone_url(auth_url, auth_version)

    args = {
        'auth_url': auth_url,
        'token': context.auth_token,
        'username': None,
        'password': None,
        'ca_file': cfg.CONF.heat_client.ca_file,
        'cert_file': cfg.CONF.heat_client.cert_file,
        'key_file': cfg.CONF.heat_client.key_file,
        'insecure': cfg.CONF.heat_client.insecure
    }

    endpoint = keystone.get_service_url(service_type='orchestration',
                                        endpoint_type=endpoint_type)

    return heatclient.Client('1', endpoint, **args)
