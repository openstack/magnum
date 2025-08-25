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

import warnings

from oslo_service import backend
import threading

import pbr.version

try:
    backend.init_backend(backend.BackendType.THREADING)
except backend.exceptions.BackendAlreadySelected:
    warnings.warn('The selected oslo_service backend is "eventlet"')

__version__ = pbr.version.VersionInfo(
    'magnum').version_string()

# Make a project global TLS trace storage repository
TLS = threading.local()
