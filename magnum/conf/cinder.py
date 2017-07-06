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
                      'value.'))]

cinder_client_opts = [
    cfg.StrOpt('region_name',
               help=_('Region in Identity service catalog to use for '
                      'communication with the OpenStack service.'))]


def register_opts(conf):
    conf.register_group(cinder_group)
    conf.register_group(cinder_client_group)
    conf.register_opts(cinder_opts, group=cinder_group)
    conf.register_opts(cinder_client_opts, group=cinder_client_group)


def list_opts():
    return {
        cinder_group: cinder_opts,
        cinder_client_group: cinder_client_opts
    }
