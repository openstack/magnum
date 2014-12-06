# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from eventlet import greenpool
from oslo.config import cfg
from oslo import messaging

from magnum.common import exception
from magnum.openstack.common import periodic_task

MANAGER_TOPIC = 'magnum_backend'


class BackendManager(periodic_task.PeriodicTasks):
    """Magnum Backend manager main class."""

    RPC_API_VERSION = '1.0'

    target = messaging.Target(version=RPC_API_VERSION)

    def __init__(self, host, topic):
        super(BackendManager, self).__init__()
        if not host:
            host = cfg.CONF.host
        self.host = host
        self.topic = topic

    def _conductor_service_record_keepalive(self):
        while not self._keepalive_evt.is_set():
            self._keepalive_evt.wait(1)

    def _spawn_worker(self, func, *args, **kwargs):

        """Create a greenthread to run func(*args, **kwargs).

        Spawns a greenthread if there are free slots in pool, otherwise raises
        exception. Execution control returns immediately to the caller.

        :returns: GreenThread object.
        :raises: NoFreeConductorWorker if worker pool is currently full.

        """
        if self._worker_pool.free():
            return self._worker_pool.spawn(func, *args, **kwargs)
        else:
            raise exception.NoFreeConductorWorker()

    def create_bay(self, context, bay):
        bay.create()
        return bay

    def init_host(self):
        self._worker_pool = greenpool.GreenPool(8)

        # Spawn a dedicated greenthread for the keepalive
#        self._keepalive_evt = threading.Event()
#        self._spawn_worker(self._conductor_service_record_keepalive)

    def del_host(self):
        pass

    def periodic_tasks(self, context, raise_on_error=False):
        """Periodic tasks are run at pre-specified interval."""
        res = self.run_periodic_tasks(context, raise_on_error=raise_on_error)
        return res

    @periodic_task.periodic_task
    def trigger(self, context):
        pass
