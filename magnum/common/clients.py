# Copyright 2014 - Rackspace Hosting.
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

from heatclient.v1 import client as heatclient
from oslo.config import cfg

from magnum.common import exception
from magnum.common import magnum_keystoneclient
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


class OpenStackClients(object):
    """Convenience class to create and cache client instances."""

    def __init__(self, context):
        self.context = context
        self._keystone = None
        self._heat = None

    def url_for(self, **kwargs):
        return self.keystone().client.service_catalog.url_for(**kwargs)

    @property
    def auth_url(self):
        return self.keystone().v3_endpoint

    @property
    def auth_token(self):
        return self.context.auth_token or self.keystone().auth_token

    def keystone(self):
        if self._keystone:
            return self._keystone

        self._keystone = magnum_keystoneclient.KeystoneClientV3(self.context)
        return self._keystone

    def _get_client_option(self, client, option):
        return getattr(getattr(cfg.CONF, '%s_client' % client), option)

    @exception.wrap_keystone_exception
    def heat(self):
        if self._heat:
            return self._heat

        endpoint_type = self._get_client_option('heat', 'endpoint_type')
        endpoint = self.url_for(service_type='orchestration',
                                endpoint_type=endpoint_type)

        args = {
            'endpoint': endpoint,
            'auth_url': self.auth_url,
            'token': self.auth_token,
            'username': None,
            'password': None,
            'ca_file': self._get_client_option('heat', 'ca_file'),
            'cert_file': self._get_client_option('heat', 'cert_file'),
            'key_file': self._get_client_option('heat', 'key_file'),
            'insecure': self._get_client_option('heat', 'insecure')
        }
        self._heat = heatclient.Client(**args)

        return self._heat
