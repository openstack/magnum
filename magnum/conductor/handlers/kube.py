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

from oslo_config import cfg

from magnum.common import clients
from magnum.common import exception
from magnum.common import k8s_manifest
from magnum.common.pythonk8sclient.client import ApivbetaApi
from magnum.common.pythonk8sclient.client import swagger
from magnum.i18n import _
from magnum import objects
from magnum.openstack.common import log as logging

import ast
from six.moves.urllib import error

LOG = logging.getLogger(__name__)


kubernetes_opts = [
    cfg.StrOpt('k8s_protocol',
               default='http',
               help=_('Default protocol of k8s master endpoint'
               ' (http or https).')),
    cfg.IntOpt('k8s_port',
               default=8080,
               help=_('Default port of the k8s master endpoint.')),
]

cfg.CONF.register_opts(kubernetes_opts, group='kubernetes')


def _retrieve_bay(context, obj):
    bay_uuid = obj.bay_uuid
    return objects.Bay.get_by_uuid(context, bay_uuid)


def _retrieve_baymodel(context, obj):
    return objects.BayModel.get_by_uuid(context, obj.baymodel_id)


def _retrieve_k8s_master_url(context, obj):
    apiserver_port = cfg.CONF.kubernetes.k8s_port
    if hasattr(obj, 'bay_uuid'):
        obj = _retrieve_bay(context, obj)

    baymodel = _retrieve_baymodel(context, obj)
    if baymodel.apiserver_port is not None:
        apiserver_port = baymodel.apiserver_port

    params = {
        'k8s_protocol': cfg.CONF.kubernetes.k8s_protocol,
        'k8s_port': apiserver_port,
        'api_address': obj.api_address
    }
    return "%(k8s_protocol)s://%(api_address)s:%(k8s_port)s" % params


def _object_has_stack(context, obj):
    osc = clients.OpenStackClients(context)
    if hasattr(obj, 'bay_uuid'):
        obj = _retrieve_bay(context, obj)

    stack = osc.heat().stacks.get(obj.stack_id)
    if (stack.stack_status == 'DELETE_COMPLETE' or
       stack.stack_status == 'DELETE_IN_PROGRESS'):
        return False
    else:
        return True


class Handler(object):
    """These are the backend operations.  They are executed by the backend
         service.  API calls via AMQP (within the ReST API) trigger the
         handlers to be called.

    """

    def __init__(self):
        super(Handler, self).__init__()
        self._k8s_api = None

    @property
    def k8s_api(self):
        return self._k8s_api

    @k8s_api.setter
    def k8s_api(self, k8s_master_url):
        """Creates connection with Kubernetes master and
            creates ApivbetaApi instance to call Kubernetes
            APIs.

            :param k8s_master_url: Kubernetes master URL
        """
        if self._k8s_api is None:
            # build a connection with Kubernetes master
            client = swagger.ApiClient(k8s_master_url)

            # create the ApivbetaApi class instance
            self._k8s_api = ApivbetaApi.ApivbetaApi(client)

    def service_create(self, context, service):
        LOG.debug("service_create")
        k8s_master_url = _retrieve_k8s_master_url(context, service)
        self.k8s_api = k8s_master_url
        manifest = k8s_manifest.parse(service.manifest)
        try:
            self.k8s_api.createService(body=manifest,
                                       namespaces='default')
        except error.HTTPError as err:
            message = ast.literal_eval(err.read())['message']
            raise exception.KubernetesAPIFailed(code=err.code, message=message)
        # call the service object to persist in db
        service.create(context)
        return service

    def service_update(self, context, service):
        LOG.debug("service_update %s", service.uuid)
        k8s_master_url = _retrieve_k8s_master_url(context, service)
        self.k8s_api = k8s_master_url
        manifest = k8s_manifest.parse(service.manifest)
        try:
            self.k8s_api.replaceService(name=service.name,
                                        body=manifest,
                                        namespaces='default')
        except error.HTTPError as err:
            message = ast.literal_eval(err.read())['message']
            raise exception.KubernetesAPIFailed(code=err.code, message=message)
        # call the service object to persist in db
        service.refresh(context)
        service.save()
        return service

    def service_delete(self, context, uuid):
        LOG.debug("service_delete %s", uuid)
        service = objects.Service.get_by_uuid(context, uuid)
        k8s_master_url = _retrieve_k8s_master_url(context, service)
        self.k8s_api = k8s_master_url
        if _object_has_stack(context, service):
            try:
                self.k8s_api.deleteService(name=service.name,
                                           namespaces='default')
            except error.HTTPError as err:
                if err.code == 404:
                    pass
                else:
                    message = ast.literal_eval(err.read())['message']
                    raise exception.KubernetesAPIFailed(code=err.code,
                                                        message=message)
        # call the service object to persist in db
        service.destroy(context)

    # Pod Operations
    def pod_create(self, context, pod):
        LOG.debug("pod_create")
        k8s_master_url = _retrieve_k8s_master_url(context, pod)
        self.k8s_api = k8s_master_url
        manifest = k8s_manifest.parse(pod.manifest)
        try:
            resp = self.k8s_api.createPod(body=manifest, namespaces='default')
        except error.HTTPError as err:
            pod.status = 'failed'
            if err.code != 409:
                pod.create(context)
            message = ast.literal_eval(err.read())['message']
            raise exception.KubernetesAPIFailed(code=err.code, message=message)
        pod.status = resp['status']['phase']
        # call the pod object to persist in db
        # TODO(yuanying): parse pod file and,
        # - extract pod name and set it
        # - extract pod labels and set it
        # TODO(yuanying): Should kube_utils support definition_url?
        # When do we get pod labels and name?
        pod.create(context)
        return pod

    def pod_update(self, context, pod):
        LOG.debug("pod_update %s", pod.uuid)
        k8s_master_url = _retrieve_k8s_master_url(context, pod)
        self.k8s_api = k8s_master_url
        manifest = k8s_manifest.parse(pod.manifest)
        try:
            self.k8s_api.replacePod(name=pod.name, body=manifest,
                                    namespaces='default')
        except error.HTTPError as err:
            message = ast.literal_eval(err.read())['message']
            raise exception.KubernetesAPIFailed(code=err.code, message=message)
        # call the pod object to persist in db
        pod.refresh(context)
        pod.save()
        return pod

    def pod_delete(self, context, uuid):
        LOG.debug("pod_delete %s", uuid)
        pod = objects.Pod.get_by_uuid(context, uuid)
        k8s_master_url = _retrieve_k8s_master_url(context, pod)
        self.k8s_api = k8s_master_url
        if _object_has_stack(context, pod):
            try:
                self.k8s_api.deletePod(name=pod.name,
                                       namespaces='default')
            except error.HTTPError as err:
                if err.code == 404:
                    pass
                else:
                    message = ast.literal_eval(err.read())['message']
                    raise exception.KubernetesAPIFailed(code=err.code,
                                                        message=message)
        # call the pod object to persist in db
        pod.destroy(context)

    # Replication Controller Operations
    def rc_create(self, context, rc):
        LOG.debug("rc_create")
        k8s_master_url = _retrieve_k8s_master_url(context, rc)
        self.k8s_api = k8s_master_url
        manifest = k8s_manifest.parse(rc.manifest)
        try:
            self.k8s_api.createReplicationController(body=manifest,
                                                     namespaces='default')
        except error.HTTPError as err:
            message = ast.literal_eval(err.read())['message']
            raise exception.KubernetesAPIFailed(code=err.code, message=message)
        # call the rc object to persist in db
        rc.create(context)
        return rc

    def rc_update(self, context, rc):
        LOG.debug("rc_update %s", rc.uuid)
        k8s_master_url = _retrieve_k8s_master_url(context, rc)
        self.k8s_api = k8s_master_url
        manifest = k8s_manifest.parse(rc.manifest)
        try:
            self.k8s_api.replaceReplicationController(name=rc.name,
                                                      body=manifest,
                                                      namespaces='default')
        except error.HTTPError as err:
            message = ast.literal_eval(err.read())['message']
            raise exception.KubernetesAPIFailed(code=err.code, message=message)
        # call the rc object to persist in db
        rc.refresh(context)
        rc.save()
        return rc

    def rc_delete(self, context, uuid):
        LOG.debug("rc_delete %s", uuid)
        rc = objects.ReplicationController.get_by_uuid(context, uuid)
        k8s_master_url = _retrieve_k8s_master_url(context, rc)
        self.k8s_api = k8s_master_url
        if _object_has_stack(context, rc):
            try:
                self.k8s_api.deleteReplicationController(name=rc.name,
                                                         namespaces='default')
            except error.HTTPError as err:
                if err.code == 404:
                    pass
                else:
                    message = ast.literal_eval(err.read())['message']
                    raise exception.KubernetesAPIFailed(code=err.code,
                                                        message=message)
        # call the rc object to persist in db
        rc.destroy(context)
