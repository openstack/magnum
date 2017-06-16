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

docker_group = cfg.OptGroup(name='docker',
                            title='Options for Docker engine')

docker_opts = [
    cfg.StrOpt('docker_remote_api_version',
               default='1.21',
               help='Docker remote api version. Override it according to '
                    'specific docker api version in your environment.'),
    cfg.IntOpt('default_timeout',
               default=60,
               help='Default timeout in seconds for docker client '
                    'operations.'),
    cfg.BoolOpt('api_insecure',
                default=False,
                help='If set, ignore any SSL validation issues'),
    cfg.StrOpt('ca_file',
               help='Location of CA certificates file for '
                    'securing docker api requests (tlscacert).'),
    cfg.StrOpt('cert_file',
               help='Location of TLS certificate file for '
                    'securing docker api requests (tlscert).'),
    cfg.StrOpt('key_file',
               help='Location of TLS private key file for '
                    'securing docker api requests (tlskey).'),
]


def register_opts(conf):
    conf.register_group(docker_group)
    conf.register_opts(docker_opts, group=docker_group)


def list_opts():
    return {
        docker_group: docker_opts
    }
