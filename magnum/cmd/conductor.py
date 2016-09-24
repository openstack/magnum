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

import os
import sys

from oslo_log import log as logging
from oslo_reports import guru_meditation_report as gmr
from oslo_service import service

from magnum.common import rpc_service
from magnum.common import service as magnum_service
from magnum.common import short_id
from magnum.conductor.handlers import ca_conductor
from magnum.conductor.handlers import cluster_conductor
from magnum.conductor.handlers import conductor_listener
from magnum.conductor.handlers import indirection_api
import magnum.conf
from magnum.i18n import _LI
from magnum import version

CONF = magnum.conf.CONF
LOG = logging.getLogger(__name__)


def main():
    magnum_service.prepare_service(sys.argv)

    gmr.TextGuruMeditation.setup_autorun(version)

    LOG.info(_LI('Starting server in PID %s'), os.getpid())
    LOG.debug("Configuration:")
    CONF.log_opt_values(LOG, logging.DEBUG)

    conductor_id = short_id.generate_id()
    endpoints = [
        indirection_api.Handler(),
        cluster_conductor.Handler(),
        conductor_listener.Handler(),
        ca_conductor.Handler(),
    ]

    server = rpc_service.Service.create(CONF.conductor.topic,
                                        conductor_id, endpoints,
                                        binary='magnum-conductor')
    launcher = service.launch(CONF, server)
    launcher.wait()
