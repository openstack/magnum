#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

"""Magnum Kubernetes RPC handler."""

from magnum.openstack.common import log as logging
from magnum.openstack.common import utils

LOG = logging.getLogger(__name__)


class Handler(object):
    """These are the backend operations.  They are executed by the backend
         service.  API calls via AMQP (within the ReST API) trigger the
         handlers to be called.

         This handler acts as an interface to executes kubectl command line
         services.
    """

    def __init__(self):
        super(Handler, self).__init__()

    @staticmethod
    def service_create(uuid, contents):
        LOG.debug("service_create %s contents %s" % (uuid, contents))
        try:
            out, err = utils.trycmd('kubectl', 'create', '-f', contents)
            if err:
                return False
        except Exception as e:
            LOG.error("Couldn't create service with contents %s \
                        due to error %s" % (contents, e))
            return False
        return True

    @staticmethod
    def service_list():
        LOG.debug("service_list")
        try:
            out = utils.execute('kubectl', 'get', 'services')
            pod_data = [s.split() for s in out.split('\n')]
            return pod_data
        except Exception as e:
            LOG.error("Couldn't get list of services due to error %s" % e)
            return None

    @staticmethod
    def service_delete(uuid):
        LOG.debug("service_delete %s" % uuid)
        try:
            out, err = utils.trycmd('kubectl', 'delete', 'service', uuid)
            if err:
                return False
        except Exception as e:
            LOG.error("Couldn't delete service  %s due to error %s"
                      % (uuid, e))
            return False
        return False

    @staticmethod
    def service_get(uuid):
        LOG.debug("service_get %s" % uuid)
        try:
            out = utils.execute('kubectl', 'get', 'service', uuid)
            # TODO(pkilambi): process the output as needed
            return out
        except Exception as e:
            LOG.error("Couldn't get service  %s due to error %s" % (uuid, e))
            return None

    @staticmethod
    def service_show(uuid):
        LOG.debug("service_show %s" % uuid)
        try:
            out = utils.execute('kubectl', 'describe', 'service', uuid)
            # TODO(pkilambi): process the output as needed
            return out
        except Exception as e:
            LOG.error("Couldn't describe service  %s due to error %s"
                      % (uuid, e))
            return None

    # Pod Operations
    @staticmethod
    def pod_create(contents):
        LOG.debug("pod_create contents %s" % contents)
        try:
            out, err = utils.trycmd('kubectl', 'create', '-f', contents)
            if err:
                return False
        except Exception as e:
            LOG.error("Couldn't create pod with contents %s due to error %s"
                      % (contents, e))
            return False
        return True

    @staticmethod
    def pod_update(contents):
        LOG.debug("pod_create contents %s" % contents)
        try:
            out, err = utils.trycmd('kubectl', 'update', '-f', contents)
            if err:
                return False
        except Exception as e:
            LOG.error("Couldn't update pod with contents %s due to error %s"
                      % (contents, e))
            return False
        return True

    @staticmethod
    def pod_list():
        LOG.debug("pod_list")
        try:
            out = utils.execute('kubectl', 'get', 'pods')
            pod_data = [s.split() for s in out.split('\n')]
            return pod_data
        except Exception as e:
            LOG.error("Couldn't get list of pods due to error %s" % e)
            return None

    @staticmethod
    def pod_delete(uuid):
        LOG.debug("pod_delete %s" % uuid)
        try:
            out, err = utils.trycmd('kubectl', 'delete', 'pod', uuid)
            if err:
                return False
        except Exception as e:
            LOG.error("Couldn't delete pod  %s due to error %s" % (uuid, e))
            return False
        return True

    @staticmethod
    def pod_get(uuid):
        LOG.debug("service_get %s" % uuid)
        try:
            out = utils.execute('kubectl', 'get', 'pod', uuid)
            # TODO(pkilambi): process the output as needed
            return out
        except Exception as e:
            LOG.error("Couldn't get service  %s due to error %s" % (uuid, e))
            return None

    @staticmethod
    def pod_show(uuid):
        LOG.debug("pod_show %s" % uuid)
        try:
            out = utils.execute('kubectl', 'describe', 'pod', uuid)
            # TODO(pkilambi): process the output as needed
            return out
        except Exception as e:
            LOG.error("Couldn't delete pod  %s due to error %s" % (uuid, e))
            return None
