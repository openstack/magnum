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

api_group = cfg.OptGroup(name='api',
                         title='Options for the magnum-api service')

api_service_opts = [
    cfg.PortOpt('port',
                default=9511,
                help='The port for the Magnum API server.'),
    cfg.IPOpt('host',
              default='127.0.0.1',
              help='The listen IP for the Magnum API server.'),
    cfg.IntOpt('max_limit',
               default=1000,
               help='The maximum number of items returned in a single '
                    'response from a collection resource.'),
    cfg.StrOpt('api_paste_config',
               default="api-paste.ini",
               help="Configuration file for WSGI definition of API."
               ),
    cfg.StrOpt('ssl_cert_file',
               help="This option allows setting path to the SSL certificate "
                    "of API server."),
    cfg.StrOpt('ssl_key_file',
               help="This option specifies the path to the file where SSL "
                    "private key of API server is stored when SSL is in "
                    "effect."),
    cfg.BoolOpt('enabled_ssl',
                default=False,
                help='Enable SSL Magnum API service'),
    cfg.IntOpt('workers',
               help='The maximum number of magnum-api processes to '
                    'fork and run. Default to number of CPUs on the host.')
]


def register_opts(conf):
    conf.register_group(api_group)
    conf.register_opts(api_service_opts, group=api_group)


def list_opts():
    return {
        api_group: api_service_opts
    }
