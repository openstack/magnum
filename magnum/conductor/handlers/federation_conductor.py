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

from magnum.common import profiler
import magnum.conf

CONF = magnum.conf.CONF


@profiler.trace_cls("rpc")
class Handler(object):

    def __init__(self):
        super(Handler, self).__init__()

    def federation_create(self, context, federation, create_timeout):
        raise NotImplementedError("This feature is not yet implemented.")

    def federation_update(self, context, federation, rollback=False):
        raise NotImplementedError("This feature is not yet implemented.")

    def federation_delete(self, context, uuid):
        raise NotImplementedError("This feature is not yet implemented.")
