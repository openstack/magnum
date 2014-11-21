# Copyright 2014 - Rackspace Hosting
#
#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

"""Starter script for the Magnum Magnum service."""

import logging as std_logging
import os
import sys

from oslo.config import cfg

from magnum.backend.handlers import docker as docker_backend
from magnum.backend.handlers import k8s as k8s_backend
from magnum.common.rpc import service
from magnum.openstack.common._i18n import _
from magnum.openstack.common import log as logging

LOG = logging.getLogger(__name__)


def main():
    cfg.CONF(sys.argv[1:], project='magnum')
    logging.setup('magnum')

    LOG.info(_('Starting server in PID %s') % os.getpid())
    LOG.debug("Configuration:")
    cfg.CONF.log_opt_values(LOG, std_logging.DEBUG)

    cfg.CONF.import_opt('topic', 'magnum.backend.config', group='backend')
    cfg.CONF.import_opt('host', 'magnum.backend.config', group='backend')
    endpoints = [
        docker_backend.Handler(),
        k8s_backend.Handler()
    ]
    server = service.Service(cfg.CONF.backend.topic,
                             cfg.CONF.backend.host, endpoints)
    server.serve()
