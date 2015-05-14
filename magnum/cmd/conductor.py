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

"""Starter script for the Magnum conductor service."""

import logging as std_logging
import os
import sys

from oslo_config import cfg

from magnum.common import rpc_service as service
from magnum.common import short_id
from magnum.conductor.handlers import bay_conductor
from magnum.conductor.handlers import conductor_listener
from magnum.conductor.handlers import docker_conductor
from magnum.conductor.handlers import kube as k8s_conductor
from magnum.i18n import _LE
from magnum.i18n import _LI
from magnum.openstack.common import log as logging

LOG = logging.getLogger(__name__)


def main():
    cfg.CONF(sys.argv[1:], project='magnum')
    logging.setup('magnum')

    LOG.info(_LI('Starting server in PID %s') % os.getpid())
    LOG.debug("Configuration:")
    cfg.CONF.log_opt_values(LOG, std_logging.DEBUG)

    cfg.CONF.import_opt('topic', 'magnum.conductor.config', group='conductor')

    conductor_id = short_id.generate_id()
    endpoints = [
        docker_conductor.Handler(),
        k8s_conductor.Handler(),
        bay_conductor.Handler(),
        conductor_listener.Handler(),
    ]

    if (not os.path.isfile(cfg.CONF.bay.k8s_atomic_template_path)
         and not os.path.isfile(cfg.CONF.bay.k8s_coreos_template_path)):
        LOG.error(_LE("The Heat template can not be found for either k8s "
                      "atomic %(atomic_template)s or coreos "
                      "(coreos_template)%s. Install template first if you "
                      "want to create bay.") %
                  {'atomic_template': cfg.CONF.bay.k8s_atomic_template_path,
                   'coreos_template': cfg.CONF.bay.k8s_coreos_template_path})

    server = service.Service(cfg.CONF.conductor.topic,
                             conductor_id, endpoints)
    server.serve()
