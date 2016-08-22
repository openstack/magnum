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

import itertools

from oslo_config import cfg

from magnum.i18n import _

# Default symbols to use for passwords. Avoids visually confusing characters.
# ~6 bits per symbol
DEFAULT_PASSWORD_SYMBOLS = ['23456789',  # Removed: 0,1
                            'ABCDEFGHJKLMNPQRSTUVWXYZ',   # Removed: I, O
                            'abcdefghijkmnopqrstuvwxyz']  # Removed: l

utils_opts = [
    cfg.StrOpt('rootwrap_config',
               default="/etc/magnum/rootwrap.conf",
               help='Path to the rootwrap configuration file to use for '
                    'running commands as root.'),
    cfg.StrOpt('tempdir',
               help='Explicitly specify the temporary working directory.'),
    cfg.ListOpt('password_symbols',
                default=DEFAULT_PASSWORD_SYMBOLS,
                help='Symbols to use for passwords')
]

periodic_opts = [
    cfg.IntOpt('service_down_time',
               default=180,
               help='Max interval size between periodic tasks execution in '
                    'seconds.'),
]

urlfetch_opts = [
    cfg.IntOpt('max_manifest_size',
               default=524288,
               help=_('Maximum raw byte size of any manifest.'))
]

ALL_OPTS = list(itertools.chain(
    utils_opts,
    periodic_opts,
    urlfetch_opts
))


def register_opts(conf):
    conf.register_opts(ALL_OPTS)


def list_opts():
    return {
        "DEFAULT": ALL_OPTS
    }
