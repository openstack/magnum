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

from oslo_log import log as logging

from magnum.common import exception
from magnum.common import k8s_manifest
from magnum.common.pythonk8sclient.swagger_client import rest
from magnum.conductor import k8s_api as k8s
from magnum.conductor import utils as conductor_utils
from magnum import objects


LOG = logging.getLogger(__name__)


class Handler(object):
    """These are the backend operations.  They are executed by the backend
         service.  API calls via AMQP (within the ReST API) trigger the
         handlers to be called.

    """

    def __init__(self):
        super(Handler, self).__init__()

    def service_create(self, context, service):
        LOG.debug("service_create")
        self.k8s_api = k8s.create_k8s_api(context, service)
        manifest = k8s_manifest.parse(service.manifest)
        try:
            self.k8s_api.create_namespaced_service(body=manifest,
                                                   namespace='default')
        except rest.ApiException as err:
            raise exception.KubernetesAPIFailed(err=err)
        # call the service object to persist in db
        service.create(context)
        return service

    def service_update(self, context, service):
        LOG.debug("service_update %s", service.uuid)
        self.k8s_api = k8s.create_k8s_api(context, service)
        manifest = k8s_manifest.parse(service.manifest)
        try:
            self.k8s_api.replace_namespaced_service(name=str(service.name),
                                                    body=manifest,
                                                    namespace='default')
        except rest.ApiException as err:
            raise exception.KubernetesAPIFailed(err=err)
        # call the service object to persist in db
        service.refresh(context)
        service.save()
        return service

    def service_delete(self, context, uuid):
        LOG.debug("service_delete %s", uuid)
        service = objects.Service.get_by_uuid(context, uuid)
        self.k8s_api = k8s.create_k8s_api(context, service)
        if conductor_utils.object_has_stack(context, service):
            try:
                self.k8s_api.delete_namespaced_service(name=str(service.name),
                                                       namespace='default')
            except rest.ApiException as err:
                if err.status == 404:
                    pass
                else:
                    raise exception.KubernetesAPIFailed(err=err)
        # call the service object to persist in db
        service.destroy(context)

    # Pod Operations
    def pod_create(self, context, pod):
        LOG.debug("pod_create")
        self.k8s_api = k8s.create_k8s_api(context, pod)
        manifest = k8s_manifest.parse(pod.manifest)
        try:
            resp = self.k8s_api.create_namespaced_pod(body=manifest,
                                                      namespace='default')
        except rest.ApiException as err:
            pod.status = 'failed'
            if err.status != 409:
                pod.create(context)
            raise exception.KubernetesAPIFailed(err=err)
        pod.status = resp.status.phase
        pod.host = resp.spec.node_name
        # call the pod object to persist in db
        # TODO(yuanying): parse pod file and,
        # - extract pod name and set it
        # - extract pod labels and set it
        # When do we get pod labels and name?
        pod.create(context)
        return pod

    def pod_update(self, context, pod):
        LOG.debug("pod_update %s", pod.uuid)
        self.k8s_api = k8s.create_k8s_api(context, pod)
        manifest = k8s_manifest.parse(pod.manifest)
        try:
            self.k8s_api.replace_namespaced_pod(name=str(pod.name),
                                                body=manifest,
                                                namespace='default')
        except rest.ApiException as err:
            raise exception.KubernetesAPIFailed(err=err)
        # call the pod object to persist in db
        pod.refresh(context)
        pod.save()
        return pod

    def pod_delete(self, context, uuid):
        LOG.debug("pod_delete %s", uuid)
        pod = objects.Pod.get_by_uuid(context, uuid)
        self.k8s_api = k8s.create_k8s_api(context, pod)
        if conductor_utils.object_has_stack(context, pod):
            try:
                self.k8s_api.delete_namespaced_pod(name=str(pod.name), body={},
                                                   namespace='default')
            except rest.ApiException as err:
                if err.status == 404:
                    pass
                else:
                    raise exception.KubernetesAPIFailed(err=err)
        # call the pod object to persist in db
        pod.destroy(context)

    # Replication Controller Operations
    def rc_create(self, context, rc):
        LOG.debug("rc_create")
        self.k8s_api = k8s.create_k8s_api(context, rc)
        manifest = k8s_manifest.parse(rc.manifest)
        try:
            self.k8s_api.create_namespaced_replication_controller(
                body=manifest, namespace='default')
        except rest.ApiException as err:
            raise exception.KubernetesAPIFailed(err=err)
        # call the rc object to persist in db
        rc.create(context)
        return rc

    def rc_update(self, context, rc):
        LOG.debug("rc_update %s", rc.uuid)
        self.k8s_api = k8s.create_k8s_api(context, rc)
        manifest = k8s_manifest.parse(rc.manifest)
        try:
            self.k8s_api.replace_namespaced_replication_controller(
                name=str(rc.name), body=manifest, namespace='default')
        except rest.ApiException as err:
            raise exception.KubernetesAPIFailed(err=err)
        # call the rc object to persist in db
        rc.refresh(context)
        rc.save()
        return rc

    def rc_delete(self, context, uuid):
        LOG.debug("rc_delete %s", uuid)
        rc = objects.ReplicationController.get_by_uuid(context, uuid)
        self.k8s_api = k8s.create_k8s_api(context, rc)
        if conductor_utils.object_has_stack(context, rc):
            try:
                self.k8s_api.delete_namespaced_replication_controller(
                    name=str(rc.name), body={}, namespace='default')
            except rest.ApiException as err:
                if err.status == 404:
                    pass
                else:
                    raise exception.KubernetesAPIFailed(err=err)
        # call the rc object to persist in db
        rc.destroy(context)
