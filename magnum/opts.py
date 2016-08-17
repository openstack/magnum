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

import magnum.api.validation
import magnum.common.cert_manager
from magnum.common.cert_manager import local_cert_manager
import magnum.common.exception
import magnum.common.rpc_service
import magnum.common.service
import magnum.common.x509.config
import magnum.conductor.config
import magnum.conductor.handlers.cluster_conductor
import magnum.db


def list_opts():
    return [
        ('DEFAULT',
         itertools.chain(magnum.common.paths.PATH_OPTS,
                         magnum.common.utils.UTILS_OPTS,
                         magnum.common.rpc_service.periodic_opts,
                         magnum.common.service.service_opts,
                         )),
        ('conductor', magnum.conductor.config.SERVICE_OPTS),
        ('database', magnum.db.sql_opts),
        ('docker', magnum.common.docker_utils.docker_opts),
        ('trust', magnum.common.keystone.trust_opts),
        ('x509', magnum.common.x509.config.x509_opts),
        ('cluster_heat',
            magnum.conductor.handlers.cluster_conductor.cluster_heat_opts),
        ('certificates',
            itertools.chain(magnum.common.cert_manager.cert_manager_opts,
                            local_cert_manager.local_cert_manager_opts,
                            )),
        ('cluster_template', magnum.api.validation.cluster_template_opts),
        ('keystone_auth', magnum.common.keystone.keystone_auth_opts),
        ('docker_registry',
         magnum.drivers.common.template_def.docker_registry_opts)
    ]
