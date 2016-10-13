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

docker_registry_group = cfg.OptGroup(name='docker_registry',
                                     title='Options for Docker Registry')

docker_registry_opts = [
    cfg.StrOpt('swift_region',
               help=_('Region name of Swift')),
    cfg.StrOpt('swift_registry_container',
               default='docker_registry',
               help=_('Name of the container in Swift which docker registry '
                      'stores images in'))
]


def register_opts(conf):
    conf.register_group(docker_registry_group)
    conf.register_opts(docker_registry_opts, group=docker_registry_group)


def list_opts():
    return {
        docker_registry_group: docker_registry_opts
    }
