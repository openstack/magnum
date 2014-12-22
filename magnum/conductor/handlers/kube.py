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

from magnum.conductor import kubecli
from magnum.openstack.common import log as logging

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
        self.kube_cli = kubecli.KubeClient()

    def service_create(self, context, service):
        LOG.debug("service_create")
        # trigger a kubectl command
        status = self.kube_cli.service_create(service)
        if not status:
            return None
        # call the service object to persist in db
        service.create(context)
        return service

    def service_update(self, context, service):
        LOG.debug("service_update")
        # trigger a kubectl command
        status = self.kube_cli.service_update(service)
        if not status:
            return None
        # call the service object to persist in db
        service.refresh(context)
        return service

    def service_list(self, context):
        LOG.debug("service_list")
        return self.kube_cli.service_list()

    def service_delete(self, context, service):
        LOG.debug("service_delete")
        # trigger a kubectl command
        status = self.kube_cli.service_delete(service.uuid)
        if not status:
            return None
        # call the service object to persist in db
        service.destroy(context)

    def service_get(self, context, uuid):
        LOG.debug("service_get")
        return self.kube_cli.service_get(uuid)

    def service_show(self, uuid):
        LOG.debug("service_show")
        return self.kube_cli.service_show(uuid)

    # Pod Operations
    def pod_create(self, context, pod):
        LOG.debug("pod_create")
        # trigger a kubectl command
        status = self.kube_cli.pod_create(pod)
        if not status:
            return None
        # call the pod object to persist in db
        pod.create(context)
        return pod

    def pod_update(self, context, pod):
        LOG.debug("pod_update")
        # trigger a kubectl command
        status = self.kube_cli.pod_update(pod)
        if not status:
            return None
        # call the pod object to persist in db
        pod.refresh(context)
        return pod

    def pod_list(self, context):
        LOG.debug("pod_list")
        return self.kube_cli.pod_list()

    def pod_delete(self, context, pod):
        LOG.debug("pod_delete ")
        # trigger a kubectl command
        status = self.kube_cli.pod_delete(pod.uuid)
        if not status:
            return None
        # call the pod object to persist in db
        pod.destroy(context)

    def pod_get(self, context, uuid):
        LOG.debug("pod_get")
        return self.kube_cli.pod_get(uuid)

    def pod_show(self, context, uuid):
        LOG.debug("pod_show")
        return self.kube_cli.pod_show(uuid)
