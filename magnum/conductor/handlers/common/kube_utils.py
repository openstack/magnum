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

import tempfile

from magnum.openstack.common import log as logging
from magnum.openstack.common import utils

LOG = logging.getLogger(__name__)


def _extract_resource_type(resource):
    return resource.__class__.__name__.lower()


def _extract_resource_data(resource):
    resource_type = _extract_resource_type(resource)
    data_attribute = "%s_data" % resource_type
    return getattr(resource, data_attribute, None)


def _extract_resource_definition_url(resource):
    resource_type = _extract_resource_type(resource)
    definition_url_attribute = "%s_definition_url" % resource_type
    return getattr(resource, definition_url_attribute, None)


def _k8s_create(master_address, resource):
    data = _extract_resource_data(resource)
    definition_url = _extract_resource_definition_url(resource)
    if data is not None:
        return _k8s_create_with_data(master_address, data)
    else:
        return _k8s_create_with_path(master_address, definition_url)


def _k8s_create_with_path(master_address, resource_file):
    return utils.trycmd('kubectl', 'create',
                        '-s', master_address,
                        '-f', resource_file)


def _k8s_create_with_data(master_address, resource_data):
    with tempfile.NamedTemporaryFile() as f:
        f.write(resource_data)
        f.flush()
        return _k8s_create_with_path(master_address, f.name)


def _k8s_update(master_address, resource):
    data = _extract_resource_data(resource)
    definition_url = _extract_resource_definition_url(resource)
    if data is not None:
        return _k8s_update_with_data(master_address, data)
    else:
        return _k8s_update_with_path(master_address, definition_url)


def _k8s_update_with_path(master_address, resource_file):
    return utils.trycmd('kubectl', 'update',
                        '-s', master_address,
                        '-f', resource_file)


def _k8s_update_with_data(master_address, resource_data):
    with tempfile.NamedTemporaryFile() as f:
        f.write(resource_data)
        f.flush()
        return _k8s_update_with_path(master_address, f.name)


class KubeClient(object):
    """These are the backend operations.  They are executed by the backend
         service.  API calls via AMQP (within the ReST API) trigger the
         handlers to be called.

         This handler acts as an interface to executes kubectl command line
         services.
    """

    def __init__(self):
        super(KubeClient, self).__init__()

    def service_create(self, master_address, service):
        LOG.debug("service_create with contents %s" % service)
        try:
            out, err = _k8s_create(master_address, service)

            if err:
                return False
        except Exception as e:
            LOG.error("Couldn't create service with contents %s \
                       due to error %s" % (service, e))
            return False
        return True

    def service_update(self, master_address, service):
        LOG.debug("service_update with contents %s" % service)
        try:
            out, err = _k8s_update(master_address, service)

            if err:
                return False
        except Exception as e:
            LOG.error("Couldn't update service with contents %s \
                       due to error %s" % (service, e))
            return False
        return True

    def service_list(self, master_address):
        LOG.debug("service_list")
        try:
            out = utils.execute('kubectl', 'get', 'services',
                                '-s', master_address,)
            pod_data = [s.split() for s in out.split('\n')]
            return pod_data
        except Exception as e:
            LOG.error("Couldn't get list of services due to error %s" % e)
            return None

    def service_delete(self, master_address, uuid):
        LOG.debug("service_delete %s" % uuid)
        try:
            out, err = utils.trycmd('kubectl', 'delete', 'service', uuid,
                                    '-s', master_address)
            if err:
                return False
        except Exception as e:
            LOG.error("Couldn't delete service %s due to error %s"
                      % (uuid, e))
            return False
        return False

    def service_get(self, master_address, uuid):
        LOG.debug("service_get %s" % uuid)
        try:
            out = utils.execute('kubectl', 'get', 'service', uuid,
                                '-s', master_address)
            # TODO(pkilambi): process the output as needed
            return out
        except Exception as e:
            LOG.error("Couldn't get service %s due to error %s" % (uuid, e))
            return None

    def service_show(self, master_address, uuid):
        LOG.debug("service_show %s" % uuid)
        try:
            out = utils.execute('kubectl', 'describe', 'service', uuid,
                                '-s', master_address)
            # TODO(pkilambi): process the output as needed
            return out
        except Exception as e:
            LOG.error("Couldn't describe service %s due to error %s"
                      % (uuid, e))
            return None

    # Pod Operations
    def pod_create(self, master_address, pod):
        LOG.debug("pod_create contents %s" % pod)
        try:
            out, err = _k8s_create(master_address, pod)

            if err:
                return False
        except Exception as e:
            LOG.error("Couldn't create pod with contents %s due to error %s"
                      % (pod, e))
            return False
        return True

    def pod_update(self, master_address, pod):
        LOG.debug("pod_update contents %s" % pod)
        try:
            out, err = _k8s_update(master_address, pod)

            if err:
                return False
        except Exception as e:
            LOG.error("Couldn't update pod with contents %s due to error %s"
                      % (pod, e))
            return False
        return True

    def pod_list(self, master_address):
        LOG.debug("pod_list")
        try:
            out = utils.execute('kubectl', 'get', 'pods', '-s', master_address)
            pod_data = [s.split() for s in out.split('\n')]
            return pod_data
        except Exception as e:
            LOG.error("Couldn't get list of pods due to error %s" % e)
            return None

    def pod_delete(self, master_address, name):
        LOG.debug("pod_delete %s" % name)
        try:
            out, err = utils.trycmd('kubectl', 'delete', 'pod', name,
                                    '-s', master_address,)
            if err:
                return False
        except Exception as e:
            LOG.error("Couldn't delete pod %s due to error %s" % (name, e))
            return False
        return True

    def pod_get(self, master_address, uuid):
        LOG.debug("pod_get %s" % uuid)
        try:
            out = utils.execute('kubectl', 'get', 'pod', uuid,
                                '-s', master_address)
            # TODO(pkilambi): process the output as needed
            return out
        except Exception as e:
            LOG.error("Couldn't get pod %s due to error %s" % (uuid, e))
            return None

    def pod_show(self, master_address, uuid):
        LOG.debug("pod_show %s" % uuid)
        try:
            out = utils.execute('kubectl', 'describe', 'pod', uuid,
                                '-s', master_address)
            # TODO(pkilambi): process the output as needed
            return out
        except Exception as e:
            LOG.error("Couldn't show pod %s due to error %s" % (uuid, e))
            return None

    # Replication Controller Operations
    def rc_create(self, master_address, rc):
        LOG.debug("rc_create contents %s" % rc)
        try:
            out, err = _k8s_create(master_address, rc)

            if err:
                return False
        except Exception as e:
            LOG.error("Couldn't create rc with contents %s due to error %s"
                      % (rc, e))
            return False
        return True

    def rc_update(self, master_address, rc):
        LOG.debug("rc_update contents %s" % rc)
        try:
            out, err = _k8s_update(master_address, rc)

            if err:
                return False
        except Exception as e:
            LOG.error("Couldn't update rc with contents %s due to error %s"
                      % (rc, e))
            return False
        return True

    def rc_delete(self, master_address, uuid):
        LOG.debug("rc_delete %s" % uuid)
        try:
            out, err = utils.trycmd('kubectl', 'delete', 'rc', uuid,
                                    '-s', master_address)
            if err:
                return False
        except Exception as e:
            LOG.error("Couldn't delete rc %s due to error %s" % (uuid, e))
            return False
        return True
