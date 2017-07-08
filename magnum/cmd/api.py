# Copyright 2013 - Red Hat, Inc.
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

"""Starter script for the Magnum API service."""

import os
import sys

from oslo_concurrency import processutils
from oslo_log import log as logging
from oslo_reports import guru_meditation_report as gmr
from werkzeug import serving

from magnum.api import app as api_app
from magnum.common import profiler
from magnum.common import service
import magnum.conf
from magnum.i18n import _
from magnum.objects import base
from magnum import version


CONF = magnum.conf.CONF
LOG = logging.getLogger(__name__)


def _get_ssl_configs(use_ssl):
    if use_ssl:
        cert_file = CONF.api.ssl_cert_file
        key_file = CONF.api.ssl_key_file

        if cert_file and not os.path.exists(cert_file):
            raise RuntimeError(
                _("Unable to find cert_file : %s") % cert_file)

        if key_file and not os.path.exists(key_file):
            raise RuntimeError(
                _("Unable to find key_file : %s") % key_file)

        return cert_file, key_file
    else:
        return None


def main():
    service.prepare_service(sys.argv)

    gmr.TextGuruMeditation.setup_autorun(version)

    # Enable object backporting via the conductor
    base.MagnumObject.indirection_api = base.MagnumObjectIndirectionAPI()

    app = api_app.load_app()

    # Setup OSprofiler for WSGI service
    profiler.setup('magnum-api', CONF.host)

    # SSL configuration
    use_ssl = CONF.api.enabled_ssl

    # Create the WSGI server and start it
    host, port = CONF.api.host, CONF.api.port

    LOG.info('Starting server in PID %s', os.getpid())
    LOG.debug("Configuration:")
    CONF.log_opt_values(LOG, logging.DEBUG)

    LOG.info('Serving on %(proto)s://%(host)s:%(port)s',
             dict(proto="https" if use_ssl else "http", host=host, port=port))

    workers = CONF.api.workers
    if not workers:
        workers = processutils.get_worker_count()
    LOG.info('Server will handle each request in a new process up to'
             ' %s concurrent processes', workers)
    serving.run_simple(host, port, app, processes=workers,
                       ssl_context=_get_ssl_configs(use_ssl))
