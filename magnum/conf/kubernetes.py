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

kubernetes_group = cfg.OptGroup(name='kubernetes',
                                title='Options for the Kubernetes addons')

kubernetes_opts = [
    cfg.StrOpt('keystone_auth_default_policy',
               default="/etc/magnum/keystone_auth_default_policy.json",
               help='Explicitly specify the path to the file defined default '
                    'Keystone auth policy for Kubernetes cluster when '
                    'the Keystone auth is enabled. Vendors can put their '
                    'specific default policy here'),
]


def register_opts(conf):
    conf.register_group(kubernetes_group)
    conf.register_opts(kubernetes_opts, group=kubernetes_group)


def list_opts():
    return {
        kubernetes_group: kubernetes_opts
    }
