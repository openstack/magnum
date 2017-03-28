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
from oslo_db import options

from magnum.conf import paths


_DEFAULT_SQL_CONNECTION = 'sqlite:///' + paths.state_path_def('magnum.sqlite')

database_group = cfg.OptGroup(name='database',
                              title='Options for Magnum Database')

sql_opts = [
    cfg.StrOpt('mysql_engine',
               default='InnoDB',
               help='MySQL engine to use.')
]


def register_opts(conf):
    conf.register_group(database_group)
    conf.register_opts(sql_opts, group=database_group)
    options.set_defaults(conf, connection=_DEFAULT_SQL_CONNECTION)


def list_opts():
    return {
        database_group: sql_opts
    }
