# Licensed under the Apache License, Version 2.0 (the "License"); you may not
# use this file except in compliance with the License. You may obtain a copy
# of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from oslo_config import cfg

from magnum.i18n import _

cinder_group = cfg.OptGroup(
    name='cinder',
    title='Options for the Cinder configuration')

cinder_client_group = cfg.OptGroup(
    name='cinder_client',
    title='Options for the Cinder client')

cinder_opts = [
    cfg.StrOpt('default_docker_volume_type',
               default='',
               help=_('The default docker volume_type to use for volumes '
                      'used for docker storage. To use the cinder volumes '
                      'for docker storage, you need to select a default '
                      'value. Otherwise, Magnum will select random one from '
                      'Cinder volume type list.')),
    cfg.StrOpt('default_etcd_volume_type',
               default='',
               help=_('The default etcd volume_type to use for volumes '
                      'used for etcd storage. To use the cinder volumes '
                      'for etcd storage, you need to select a default '
                      'value. Otherwise, Magnum will select random one from '
                      'Cinder volume type list.')),
    cfg.StrOpt('default_boot_volume_type',
               default='',
               help=_('The default boot volume_type to use for volumes '
                      'used for VM of COE. To use the cinder volumes '
                      'for VM of COE, you need to select a default '
                      'value. Otherwise, Magnum will select random one from '
                      'Cinder volume type list.')),
    cfg.IntOpt('default_boot_volume_size',
               default=0,
               help=_('The default volume size to use for volumes '
                      'used for VM of COE.'))
]

cinder_client_opts = [
    cfg.StrOpt('region_name',
               help=_('Region in Identity service catalog to use for '
                      'communication with the OpenStack service.')),
    cfg.StrOpt('endpoint_type',
               default='publicURL',
               help=_('Type of endpoint in Identity service catalog to use '
                      'for communication with the OpenStack service.')),
    cfg.StrOpt('api_version',
               default='3',
               help=_('Version of Cinder API to use in cinderclient.'))
]

common_security_opts = [
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


def register_opts(conf):
    conf.register_group(cinder_group)
    conf.register_group(cinder_client_group)
    conf.register_opts(cinder_opts, group=cinder_group)
    conf.register_opts(cinder_client_opts, group=cinder_client_group)
    conf.register_opts(common_security_opts, group=cinder_client_group)


def list_opts():
    return {
        cinder_group: cinder_opts,
        cinder_client_group: cinder_client_opts
    }
