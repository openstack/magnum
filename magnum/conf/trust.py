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

trust_group = cfg.OptGroup(name='trust',
                           title='Trustee options for the magnum services')

trust_opts = [
    cfg.StrOpt('trustee_domain_id',
               help=_('Id of the domain to create trustee for clusters')),
    cfg.StrOpt('trustee_domain_name',
               help=_('Name of the domain to create trustee for s')),
    cfg.StrOpt('trustee_domain_admin_id',
               help=_('Id of the admin with roles sufficient to manage users'
                      ' in the trustee_domain')),
    cfg.StrOpt('trustee_domain_admin_name',
               help=_('Name of the admin with roles sufficient to manage users'
                      ' in the trustee_domain')),
    cfg.StrOpt('trustee_domain_admin_domain_id',
               help=_('Id of the domain admin user\'s domain.'
                      ' trustee_domain_id is used by default')),
    cfg.StrOpt('trustee_domain_admin_domain_name',
               help=_('Name of the domain admin user\'s domain.'
                      ' trustee_domain_name is used by default')),
    cfg.StrOpt('trustee_domain_admin_password', secret=True,
               help=_('Password of trustee_domain_admin')),
    cfg.ListOpt('roles',
                default=[],
                help=_('The roles which are delegated to the trustee '
                       'by the trustor'))
]


def register_opts(conf):
    conf.register_group(trust_group)
    conf.register_opts(trust_opts, group=trust_group)


def list_opts():
    return {
        trust_group: trust_opts
    }
