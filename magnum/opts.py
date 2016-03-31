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
import magnum.api.validation
import magnum.common.cert_manager
from magnum.common.cert_manager import local_cert_manager
import magnum.common.clients
import magnum.common.exception
import magnum.common.service
import magnum.common.x509.config
import magnum.conductor.config
import magnum.conductor.handlers.bay_conductor
import magnum.conductor.handlers.docker_conductor
import magnum.conductor.handlers.k8s_conductor
import magnum.conductor.template_definition
import magnum.db


def list_opts():
    return [
        ('DEFAULT',
         itertools.chain(magnum.common.paths.PATH_OPTS,
                         magnum.common.utils.UTILS_OPTS,
                         magnum.common.rpc_service.periodic_opts,
                         magnum.common.service.service_opts,
                         )),
        ('api', magnum.api.app.API_SERVICE_OPTS),
        ('bay', magnum.conductor.template_definition.template_def_opts),
        ('conductor', magnum.conductor.config.SERVICE_OPTS),
        ('database', magnum.db.sql_opts),
        ('docker', magnum.common.docker_utils.docker_opts),
        ('trust', magnum.common.keystone.trust_opts),
        ('magnum_client', magnum.common.clients.magnum_client_opts),
        ('heat_client', magnum.common.clients.heat_client_opts),
        ('glance_client', magnum.common.clients.glance_client_opts),
        ('barbican_client', magnum.common.clients.barbican_client_opts),
        ('cinder_client', magnum.common.clients.cinder_client_opts),
        ('nova_client', magnum.common.clients.nova_client_opts),
        ('neutron_client', magnum.common.clients.neutron_client_opts),
        ('x509', magnum.common.x509.config.x509_opts),
        ('bay_heat', magnum.conductor.handlers.bay_conductor.bay_heat_opts),
        ('certificates',
            itertools.chain(magnum.common.cert_manager.cert_manager_opts,
                            local_cert_manager.local_cert_manager_opts,
                            )),
        ('baymodel', magnum.api.validation.baymodel_opts),
        ('keystone_auth', magnum.common.keystone.keystone_auth_opts),
        ('docker_registry',
         magnum.conductor.template_definition.docker_registry_opts)
    ]
