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

from magnum.common import exception
from magnum.i18n import _LE
from magnum.openstack.common import log as logging
from magnum.openstack.common import utils

LOG = logging.getLogger(__name__)


def _k8s_create(api_address, resource):
    data = resource.manifest
    definition_url = resource.manifest_url
    if data is not None:
        return _k8s_create_with_data(api_address, data)
    else:
        return _k8s_create_with_path(api_address, definition_url)


def _k8s_create_with_path(api_address, resource_file):
    return utils.trycmd('kubectl', 'create',
                        '-s', api_address,
                        '-f', resource_file)


def _k8s_create_with_data(api_address, resource_data):
    with tempfile.NamedTemporaryFile() as f:
        f.write(resource_data)
        f.flush()
        return _k8s_create_with_path(api_address, f.name)


def _k8s_update(api_address, resource):
    data = resource.manifest
    definition_url = resource.manifest_url
    if data is not None:
        return _k8s_update_with_data(api_address, data)
    else:
        return _k8s_update_with_path(api_address, definition_url)


def _k8s_update_with_path(api_address, resource_file):
    return utils.trycmd('kubectl', 'update',
                        '-s', api_address,
                        '-f', resource_file)


def _k8s_update_with_data(api_address, resource_data):
    with tempfile.NamedTemporaryFile() as f:
        f.write(resource_data)
        f.flush()
        return _k8s_update_with_path(api_address, f.name)


class KubeClient(object):
    """These are the backend operations.  They are executed by the backend
         service.  API calls via AMQP (within the ReST API) trigger the
         handlers to be called.

         This handler acts as an interface to executes kubectl command line
         services.
    """

    def __init__(self):
        super(KubeClient, self).__init__()

    def service_create(self, api_address, service):
        LOG.debug("service_create with contents %s" % service.as_dict())
        try:
            out, err = _k8s_create(api_address, service)

            if err:
                return False
        except Exception as e:
            LOG.error(_LE("Couldn't create service with contents %(content)s "
                          "due to error %(error)s") %
                      {'content': service, 'error': e})
            return False
        return True

    def service_update(self, api_address, service):
        LOG.debug("service_update with contents %s" % service.as_dict())
        try:
            out, err = _k8s_update(api_address, service)

            if err:
                return False
        except Exception as e:
            LOG.error(_LE("Couldn't update service with contents %(content)s "
                          "due to error %(error)s") %
                      {'content': service, 'error': e})
            return False
        return True

    def service_delete(self, api_address, name):
        LOG.debug("service_delete %s" % name)
        try:
            out, err = utils.trycmd('kubectl', 'delete', 'service', name,
                                    '-s', api_address)
            if err:
                return False
        except Exception as e:
            LOG.error(_LE("Couldn't delete service %(service)s due to error "
                          "%(error)s") % {'service': name, 'error': e})
            return False
        return True

    # Pod Operations
    def pod_create(self, api_address, pod):
        LOG.debug("pod_create contents %s" % pod.as_dict())
        try:
            out, err = _k8s_create(api_address, pod)

            if err:
                return False
        except Exception as e:
            LOG.error(_LE("Couldn't create pod with contents %(content)s "
                          "due to error %(error)s") %
                      {'content': pod, 'error': e})
            return False
        return True

    def pod_update(self, api_address, pod):
        LOG.debug("pod_update contents %s" % pod.as_dict())
        try:
            out, err = _k8s_update(api_address, pod)

            if err:
                return False
        except Exception as e:
            LOG.error(_LE("Couldn't update pod with %(content)s due to error "
                          "%(error)s") % {'content': pod, 'error': e})
            return False
        return True

    def pod_delete(self, api_address, name):
        LOG.debug("pod_delete %s" % name)
        try:
            out, err = utils.trycmd('kubectl', 'delete', 'pod', name,
                                    '-s', api_address,)
        except Exception as e:
            LOG.error(_LE("Couldn't delete pod %(pod)s due to error "
                          "%(error)s") % {'pod': name, 'error': e})
            return False

        if err:
            if ('"%s" not found' % name) in err:
                raise exception.PodNotFound(pod=name)
            else:
                return False

        return True

    # Replication Controller Operations
    def rc_create(self, api_address, rc):
        LOG.debug("rc_create contents %s" % rc.as_dict())
        try:
            out, err = _k8s_create(api_address, rc)

            if err:
                return False
        except Exception as e:
            LOG.error(_LE("Couldn't create rc with contents %(content)s due "
                          "error %(error)s") % {'content': rc, 'error': e})
            return False
        return True

    def rc_update(self, api_address, rc):
        LOG.debug("rc_update contents %s" % rc.as_dict())
        try:
            out, err = _k8s_update(api_address, rc)

            if err:
                return False
        except Exception as e:
            LOG.error(_LE("Couldn't update rc with contents %(content)s due "
                          "to error %(error)s") % {'content': rc, 'error': e})
            return False
        return True

    def rc_delete(self, api_address, name):
        LOG.debug("rc_delete %s" % name)
        try:
            out, err = utils.trycmd('kubectl', 'delete', 'rc', name,
                                    '-s', api_address)
            if err:
                return False
        except Exception as e:
            LOG.error(_LE("Couldn't delete rc %(rc)s due to error %(error)s")
                      % {'rc': name, 'error': e})
            return False
        return True
