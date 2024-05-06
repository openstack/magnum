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

drivers_group = cfg.OptGroup(name='drivers',
                             title='Options for the Drivers')

drivers_opts = [
    cfg.BoolOpt('verify_ca',
                default=True,
                help='Indicates whether the cluster nodes validate the '
                     'Certificate Authority when making requests to the '
                     'OpenStack APIs (Keystone, Magnum, Heat). If you have '
                     'self-signed certificates for the OpenStack APIs or '
                     'you have your own Certificate Authority and you '
                     'have not installed the Certificate Authority to all '
                     'nodes, you may need to disable CA validation by '
                     'setting this flag to False.'),
    cfg.StrOpt('openstack_ca_file',
               default="",
               help='Path to the OpenStack CA-bundle file to pass and '
                    'install in all cluster nodes.'),
    cfg.ListOpt('disabled_drivers',
                default=[],
                help='Disabled driver entry points. If empty, then all '
                     'available drivers are enabled.'
                ),
    cfg.ListOpt('enabled_beta_drivers',
                default=[],
                help='List of beta drivers to enable. Beta drivers are not '
                     'intended for production.'
                ),
]


def register_opts(conf):
    conf.register_group(drivers_group)
    conf.register_opts(drivers_opts, group=drivers_group)


def list_opts():
    return {
        drivers_group: drivers_opts,
    }
