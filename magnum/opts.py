# Copyright 2014
# The Cloudscaling Group, Inc.
#
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

import magnum.api.app
import magnum.api.auth
import magnum.common.clients
import magnum.common.exception
import magnum.common.magnum_keystoneclient
import magnum.conductor.config
import magnum.conductor.handlers.bay_conductor
import magnum.conductor.handlers.docker_conductor
import magnum.conductor.handlers.k8s_conductor
import magnum.conductor.template_definition
import magnum.db.sqlalchemy.models


def list_opts():
    return [
        ('DEFAULT',
         itertools.chain(magnum.api.auth.AUTH_OPTS,
                         magnum.common.magnum_keystoneclient.trust_opts,
                         magnum.common.paths.PATH_OPTS,
                         magnum.common.utils.UTILS_OPTS,
                         magnum.common.rpc_service.periodic_opts
                         )),
        ('api', magnum.api.app.API_SERVICE_OPTS),
        ('bay', magnum.conductor.template_definition.template_def_opts),
        ('conductor', magnum.conductor.config.SERVICE_OPTS),
        ('database', magnum.db.sqlalchemy.models.sql_opts),
        ('docker', magnum.conductor.handlers.docker_conductor.docker_opts),
        ('heat_client', magnum.common.clients.heat_client_opts),
        ('glance_client', magnum.common.clients.glance_client_opts),
        ('bay_heat', magnum.conductor.handlers.bay_conductor.bay_heat_opts),
        ('kubernetes',
            magnum.conductor.k8s_api.kubernetes_opts),
    ]
