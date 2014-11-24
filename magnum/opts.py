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
import magnum.backend.config
import magnum.conductor.config


def list_opts():
    return [
        ('DEFAULT',
         itertools.chain(magnum.api.app.API_SERVICE_OPTS,
                         magnum.api.auth.AUTH_OPTS,)),
        ('conductor', magnum.conductor.config.SERVICE_OPTS),
    ]
