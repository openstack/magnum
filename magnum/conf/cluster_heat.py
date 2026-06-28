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

cluster_heat_group = cfg.OptGroup(name='cluster_heat',
                                  title='Heat options for Cluster '
                                        'configuration')

cluster_heat_opts = [
    cfg.IntOpt('max_attempts',
               default=2000,
               help=('Number of attempts to query the Heat stack for '
                     'finding out the status of the created stack and '
                     'getting template outputs.  This value is ignored '
                     'during cluster creation if timeout is set as the poll '
                     'will continue until cluster creation either ends '
                     'or times out.'),
               deprecated_group='bay_heat'),
    cfg.IntOpt('wait_interval',
               default=1,
               help=('Sleep time interval between two attempts of querying '
                     'the Heat stack.  This interval is in seconds.'),
               deprecated_group='bay_heat'),
    cfg.IntOpt('create_timeout',
               default=60,
               help=('The length of time to let cluster creation continue. '
                     'This interval is in minutes. The default is 60 minutes.'
                     ),
               deprecated_group='bay_heat',
               deprecated_name='bay_create_timeout'),
    cfg.IntOpt('update_timeout',
               default=90,
               help=('The length of time to let cluster update operations '
                     'such as upgrade and CA rotation continue. This '
                     'interval is in minutes. The default is 90 minutes. '
                     'CA rotation runs a multi-phase prepare/cutover/finalize '
                     'protocol coordinated across all nodes, so this must '
                     'comfortably exceed the time for the slowest node to '
                     'complete all phases (control-plane restarts plus '
                     'cluster-wide barriers).')),
    cfg.IntOpt('update_timeout_per_node',
               default=30,
               help=('Extra Heat stack-update budget, in minutes, granted per '
                     'node beyond the first during upgrade, reconfigure and CA '
                     'rotation. Batch-1 rolling updates converge nodes '
                     'serially, so the whole-stack timeout must cover the '
                     'slowest serial chain rather than a single node. The '
                     'effective timeout is update_timeout + '
                     'update_timeout_per_node * (master_count + node_count - '
                     '1). It is a ceiling, not a wait: healthy updates still '
                     'finish early. Set to 0 to restore the flat '
                     'update_timeout behaviour. Raise it for slow first '
                     'old->new migrations or low-RAM nodes where a single '
                     'node reconcile can take 20-30 minutes.'))
]


def register_opts(conf):
    conf.register_group(cluster_heat_group)
    conf.register_opts(cluster_heat_opts, group=cluster_heat_group)


def list_opts():
    return {
        cluster_heat_group: cluster_heat_opts
    }
