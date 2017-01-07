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

quotas_group = cfg.OptGroup(name='quotas',
                            title='Options for quota configuration')

quotas_def_opts = [
    cfg.IntOpt('max_clusters_per_project',
               default=20,
               help=_('Max number of clusters allowed per project. Admin can '
                      'override this default quota for a project by setting '
                      'explicit limit in quotas DB table (using /quotas REST '
                      'API endpoint).')),
]


def register_opts(conf):
    conf.register_group(quotas_group)
    conf.register_opts(quotas_def_opts, group=quotas_group)


def list_opts():
    return {
        quotas_group: quotas_def_opts
    }
