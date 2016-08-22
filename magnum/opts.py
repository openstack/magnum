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

import magnum.common.cert_manager
from magnum.common.cert_manager import local_cert_manager
import magnum.common.docker_utils
import magnum.common.exception
import magnum.common.x509.config
import magnum.db
import magnum.drivers.common.template_def


def list_opts():
    return [
        ('docker', magnum.common.docker_utils.docker_opts),
        ('trust', magnum.common.keystone.trust_opts),
        ('x509', magnum.common.x509.config.x509_opts),
        ('certificates',
            itertools.chain(magnum.common.cert_manager.cert_manager_opts,
                            local_cert_manager.local_cert_manager_opts,
                            )),
        ('keystone_auth', magnum.common.keystone.keystone_auth_opts),
        ('docker_registry',
         magnum.drivers.common.template_def.docker_registry_opts)
    ]
