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

cluster_group = cfg.OptGroup(name='cluster',
                             title='Options for Cluster configuration')

cluster_def_opts = [
    cfg.StrOpt('etcd_discovery_service_endpoint_format',
               default='https://discovery.etcd.io/new?size=%(size)d',
               help=_('Url for etcd public discovery endpoint.'),
               deprecated_group='bay'),
    cfg.StrOpt('nodes_affinity_policy',
               default='soft-anti-affinity',
               help=_('Affinity policy for server group of cluster nodes. '
                      'Possible values include "affinity", "anti-affinity", '
                      '"soft-affinity" and "soft-anti-affinity".')
               ),
    cfg.StrOpt('temp_cache_dir',
               default="/var/lib/magnum/certificate-cache",
               help='Explicitly specify the temporary directory to hold '
                    'cached TLS certs.'),
    cfg.IntOpt('pre_delete_lb_timeout',
               default=60,
               help=_('The timeout in seconds to wait for the load balancers '
                      'to be deleted.')),
]


def register_opts(conf):
    conf.register_group(cluster_group)
    conf.register_opts(cluster_def_opts, group=cluster_group)


def list_opts():
    return {
        cluster_group: cluster_def_opts
    }
