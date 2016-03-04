# Copyright 2013 - Red Hat, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import socket

from oslo_config import cfg
from oslo_log import log as logging

from magnum.common import config
from magnum.i18n import _


service_opts = [
    cfg.StrOpt('host',
               default=socket.getfqdn(),
               help=_('Name of this node. This can be an opaque identifier. '
                      'It is not necessarily a hostname, FQDN, or IP address. '
                      'However, the node name must be valid within '
                      'an AMQP key, and if using ZeroMQ, a valid '
                      'hostname, FQDN, or IP address.')),
]

cfg.CONF.register_opts(service_opts)


def prepare_service(argv=None):
    if argv is None:
        argv = []
    logging.register_options(cfg.CONF)
    config.parse_args(argv)
    config.set_config_defaults()

    logging.setup(cfg.CONF, 'magnum')
