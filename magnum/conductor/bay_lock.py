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

import contextlib

from oslo_config import cfg
from oslo_log import log as logging
import oslo_messaging as messaging
from oslo_utils import excutils

from magnum.common import exception
from magnum.conductor.api import ListenerAPI
from magnum.i18n import _LI
from magnum.i18n import _LW
from magnum import objects


cfg.CONF.import_opt('topic', 'magnum.conductor.config',
                    group='conductor')
cfg.CONF.import_opt('conductor_life_check_timeout', 'magnum.conductor.config',
                    group='conductor')


LOG = logging.getLogger(__name__)


class BayLock(object):

    def __init__(self, context, bay, conductor_id):
        self.context = context
        self.bay = bay
        self.conductor_id = conductor_id

    @staticmethod
    def conductor_alive(context, conductor_id):
        topic = cfg.CONF.conductor.topic
        timeout = cfg.CONF.conductor.conductor_life_check_timeout
        listener_api = ListenerAPI(context=context, topic=topic,
                                   server=conductor_id, timeout=timeout)
        try:
            return listener_api.ping_conductor()
        except messaging.MessagingTimeout:
            return False

    def acquire(self, retry=True):
        """Acquire a lock on the bay.

        :param retry: When True, retry if lock was released while stealing.
        """
        lock_conductor_id = objects.BayLock.create(self.bay.uuid,
                                                   self.conductor_id)
        if lock_conductor_id is None:
            LOG.debug("Conductor %(conductor)s acquired lock on bay "
                      "%(bay)s" % {'conductor': self.conductor_id,
                                   'bay': self.bay.uuid})
            return

        if (lock_conductor_id == self.conductor_id or
                self.conductor_alive(self.context, lock_conductor_id)):
            LOG.debug("Lock on bay %(bay)s is owned by conductor "
                      "%(conductor)s" % {'bay': self.bay.uuid,
                                         'conductor': lock_conductor_id})
            raise exception.OperationInProgress(bay_name=self.bay.name)
        else:
            LOG.info(_LI("Stale lock detected on bay %(bay)s.  Conductor "
                         "%(conductor)s will attempt to steal the lock"),
                     {'bay': self.bay.uuid, 'conductor': self.conductor_id})

            result = objects.BayLock.steal(self.bay.uuid,
                                           lock_conductor_id,
                                           self.conductor_id)

            if result is None:
                LOG.info(_LI("Conductor %(conductor)s successfully stole the "
                             "lock on bay %(bay)s"),
                         {'conductor': self.conductor_id,
                          'bay': self.bay.uuid})
                return
            elif result is True:
                if retry:
                    LOG.info(_LI("The lock on bay %(bay)s was released while "
                                 "conductor %(conductor)s was stealing it. "
                                 "Trying again"),
                             {'bay': self.bay.uuid,
                              'conductor': self.conductor_id})
                    return self.acquire(retry=False)
            else:
                new_lock_conductor_id = result
                LOG.info(_LI("Failed to steal lock on bay %(bay)s. "
                             "Conductor %(conductor)s stole the lock first"),
                         {'bay': self.bay.uuid,
                          'conductor': new_lock_conductor_id})

            raise exception.OperationInProgress(bay_name=self.bay.name)

    def release(self, bay_uuid):
        """Release a bay lock."""
        # Only the conductor that owns the lock will be releasing it.
        result = objects.BayLock.release(bay_uuid, self.conductor_id)
        if result is True:
            LOG.warn(_LW("Lock was already released on bay %s!"), bay_uuid)
        else:
            LOG.debug("Conductor %(conductor)s released lock on bay "
                      "%(bay)s" % {'conductor': self.conductor_id,
                                   'bay': bay_uuid})

    @contextlib.contextmanager
    def thread_lock(self, bay_uuid):
        """Acquire a lock and release it only if there is an exception.
        The release method still needs to be scheduled to be run at the
        end of the thread using the Thread.link method.
        """
        try:
            self.acquire()
            yield
        except exception.OperationInProgress:
            raise
        except:  # noqa
            with excutils.save_and_reraise_exception():
                self.release(bay_uuid)
