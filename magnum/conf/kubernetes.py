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
    cfg.StrOpt('post_install_manifest_url',
               default="",
               help='An URL of the manifest file will be installed after '
                    'the Kubernetes cluster created. For exmaple, this '
                    'could be a file including the vendor specific '
                    'storage class.'),
    cfg.IntOpt('health_polling_interval',
               default=60,
               help=('The default polling interval for Kubernetes cluster '
                     'health. If this number is negative the periodic task '
                     'will be disabled.')),
]


def register_opts(conf):
    conf.register_group(kubernetes_group)
    conf.register_opts(kubernetes_opts, group=kubernetes_group)


def list_opts():
    return {
        kubernetes_group: kubernetes_opts
    }
