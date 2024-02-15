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

cluster_template_group = cfg.OptGroup(name='cluster_template',
                                      title='Options for cluster_template')

cluster_template_opts = [
    cfg.ListOpt('kubernetes_allowed_network_drivers',
                default=['flannel', 'calico'],
                help=_("Allowed network drivers for kubernetes."),
                ),
    cfg.StrOpt('kubernetes_default_network_driver',
               default='flannel',
               help=_("Default network driver for kubernetes "
                      "cluster-templates."),
               ),
]


def register_opts(conf):
    conf.register_group(cluster_template_group)
    conf.register_opts(cluster_template_opts, group=cluster_template_group)


def list_opts():
    return {
        cluster_template_group: cluster_template_opts
    }
