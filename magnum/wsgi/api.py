# -*- mode: python -*-
#
# Copyright 2017 SUSE Linux GmbH
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import sys

from oslo_log import log as logging

from magnum.api import app as api_app
from magnum.common import service
import magnum.conf
from magnum.drivers.common import driver as driver_module

CONF = magnum.conf.CONF
LOG = logging.getLogger(__name__)

service.prepare_service(sys.argv)

LOG.debug("Configuration:")
CONF.log_opt_values(LOG, logging.DEBUG)

drivers = [ep.name for ep, _ in driver_module.Driver.load_entry_points()]
LOG.debug('Loaded drivers: %s', drivers)

application = api_app.load_app()
