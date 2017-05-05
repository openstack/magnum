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

conductor_group = cfg.OptGroup(name='conductor',
                               title='Options for the magnum-conductor '
                                     'service')

conductor_service_opts = [
    cfg.StrOpt('topic',
               default='magnum-conductor',
               help='The queue to add conductor tasks to.'),
    cfg.IntOpt('conductor_life_check_timeout',
               default=4,
               help=('RPC timeout for the conductor liveness check that is '
                     'used for cluster locking.')),
    cfg.IntOpt('workers',
               help='Number of magnum-conductor processes to fork and run. '
                    'Default to number of CPUs on the host.')
]


def register_opts(conf):
    conf.register_group(conductor_group)
    conf.register_opts(conductor_service_opts, group=conductor_group)


def list_opts():
    return {
        conductor_group: conductor_service_opts
    }
