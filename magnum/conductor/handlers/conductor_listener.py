# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

from magnum.common import profiler


@profiler.trace_cls("rpc")
class Handler(object):
    """Listen on an AMQP queue named for the conductor.

    Allows individual conductors to communicate with each other for
    multi-conductor support.
    """
    def ping_conductor(self, context):
        """Respond to conductor.

        Respond affirmatively to confirm that the conductor performing the
        action is still alive.
        """
        return True
