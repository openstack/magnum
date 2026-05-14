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

from keystoneauth1 import loading as ka_loading
from oslo_config import cfg

CFG_GROUP = 'keystone_auth'
CFG_LEGACY_GROUP = 'keystone_authtoken'

keystone_auth_group = cfg.OptGroup(name=CFG_GROUP,
                                   title='Options for Keystone in Magnum')


def register_opts(conf):
    ka_loading.register_auth_conf_options(conf, CFG_GROUP)
    ka_loading.register_session_conf_options(conf, CFG_GROUP)
    conf.set_default('auth_type', default='password', group=CFG_GROUP)


def list_opts():
    keystone_auth_opts = (ka_loading.get_auth_common_conf_options() +
                          ka_loading.get_auth_plugin_conf_options('password'))
    return {
        keystone_auth_group: keystone_auth_opts
    }
