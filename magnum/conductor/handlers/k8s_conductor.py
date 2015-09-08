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


from oslo_log import log as logging

from magnum.common import exception
from magnum.common import k8s_manifest
from magnum.common.pythonk8sclient.swagger_client import rest
from magnum.common import utils
from magnum.conductor import k8s_api as k8s
from magnum.conductor import utils as conductor_utils
from magnum import objects

import ast


LOG = logging.getLogger(__name__)


class Handler(object):
    """Magnum Kubernetes RPC handler.

    These are the backend operations. They are executed by the backend service.
    API calls via AMQP (within the ReST API) trigger the handlers to be called.

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
        self.k8s_api = k8s.create_k8s_api_rc(context, rc.bay_uuid)
        manifest = k8s_manifest.parse(rc.manifest)
        try:
            resp = self.k8s_api.create_namespaced_replication_controller(
                body=manifest,
                namespace='default')
        except rest.ApiException as err:
            raise exception.KubernetesAPIFailed(err=err)

        if resp is None:
            raise exception.ReplicationControllerCreationFailed(
                bay_uuid=rc.bay_uuid)

        rc['uuid'] = resp.metadata.uid
        rc['name'] = resp.metadata.name
        rc['images'] = [c.image for c in resp.spec.template.spec.containers]
        rc['labels'] = ast.literal_eval(resp.metadata.labels)
        rc['replicas'] = resp.status.replicas
        return rc

    def rc_update(self, context, rc_ident, bay_ident, manifest):
        LOG.debug("rc_update %s", rc_ident)
        # Since bay identifier is specified verify whether its a UUID
        # or Name. If name is specified as bay identifier need to extract
        # the bay uuid since its needed to get the k8s_api object.
        if not utils.is_uuid_like(bay_ident):
            bay = objects.Bay.get_by_name(context, bay_ident)
            bay_ident = bay.uuid

        bay_uuid = bay_ident
        self.k8s_api = k8s.create_k8s_api_rc(context, bay_uuid)
        if utils.is_uuid_like(rc_ident):
            rc = objects.ReplicationController.get_by_uuid(context, rc_ident,
                                                           bay_uuid,
                                                           self.k8s_api)
        else:
            rc = objects.ReplicationController.get_by_name(context, rc_ident,
                                                           bay_uuid,
                                                           self.k8s_api)
        try:
            resp = self.k8s_api.replace_namespaced_replication_controller(
                name=str(rc.name),
                body=manifest,
                namespace='default')
        except rest.ApiException as err:
            raise exception.KubernetesAPIFailed(err=err)

        if resp is None:
            raise exception.ReplicationControllerNotFound(rc=rc.uuid)

        rc['uuid'] = resp.metadata.uid
        rc['name'] = resp.metadata.name
        rc['project_id'] = context.project_id
        rc['user_id'] = context.user_id
        rc['images'] = [c.image for c in resp.spec.template.spec.containers]
        rc['bay_uuid'] = bay_uuid
        rc['labels'] = ast.literal_eval(resp.metadata.labels)
        rc['replicas'] = resp.status.replicas

        return rc

    def rc_delete(self, context, rc_ident, bay_ident):
        LOG.debug("rc_delete %s", rc_ident)
        # Since bay identifier is specified verify whether its a UUID
        # or Name. If name is specified as bay identifier need to extract
        # the bay uuid since its needed to get the k8s_api object.
        if not utils.is_uuid_like(bay_ident):
            bay = objects.Bay.get_by_name(context, bay_ident)
            bay_ident = bay.uuid

        bay_uuid = bay_ident
        self.k8s_api = k8s.create_k8s_api_rc(context, bay_uuid)
        if utils.is_uuid_like(rc_ident):
            rc = objects.ReplicationController.get_by_uuid(context, rc_ident,
                                                           bay_uuid,
                                                           self.k8s_api)
            rc_name = rc.name
        else:
            rc_name = rc_ident
        if conductor_utils.object_has_stack(context, bay_uuid):
            try:
                self.k8s_api.delete_namespaced_replication_controller(
                    name=str(rc_name),
                    body={},
                    namespace='default')
            except rest.ApiException as err:
                if err.status == 404:
                    pass
                else:
                    raise exception.KubernetesAPIFailed(err=err)

    def rc_show(self, context, rc_ident, bay_ident):
        LOG.debug("rc_show %s", rc_ident)
        # Since bay identifier is specified verify whether its a UUID
        # or Name. If name is specified as bay identifier need to extract
        # the bay uuid since its needed to get the k8s_api object.
        if not utils.is_uuid_like(bay_ident):
            bay = objects.Bay.get_by_name(context, bay_ident)
            bay_ident = bay.uuid

        bay_uuid = bay_ident
        self.k8s_api = k8s.create_k8s_api_rc(context, bay_uuid)
        if utils.is_uuid_like(rc_ident):
            rc = objects.ReplicationController.get_by_uuid(context, rc_ident,
                                                           bay_uuid,
                                                           self.k8s_api)
        else:
            rc = objects.ReplicationController.get_by_name(context, rc_ident,
                                                           bay_uuid,
                                                           self.k8s_api)

        return rc

    def rc_list(self, context, bay_ident):
        # Since bay identifier is specified verify whether its a UUID
        # or Name. If name is specified as bay identifier need to extract
        # the bay uuid since its needed to get the k8s_api object.
        if not utils.is_uuid_like(bay_ident):
            bay = objects.Bay.get_by_name(context, bay_ident)
            bay_ident = bay.uuid

        bay_uuid = bay_ident
        self.k8s_api = k8s.create_k8s_api_rc(context, bay_uuid)
        try:
            resp = self.k8s_api.list_namespaced_replication_controller(
                namespace='default')
        except rest.ApiException as err:
            raise exception.KubernetesAPIFailed(err=err)

        if resp is None:
            raise exception.ReplicationControllerListNotFound(
                bay_uuid=bay_uuid)

        rcs = []
        for entry in resp._items:
            rc = {}
            rc['uuid'] = entry.metadata.uid
            rc['name'] = entry.metadata.name
            rc['project_id'] = context.project_id
            rc['user_id'] = context.user_id
            rc['images'] = [
                c.image for c in entry.spec.template.spec.containers]
            rc['bay_uuid'] = bay_uuid
            # Convert string to dictionary
            rc['labels'] = ast.literal_eval(entry.metadata.labels)
            rc['replicas'] = entry.status.replicas

            rc_obj = objects.ReplicationController(context, **rc)
            rcs.append(rc_obj)

        return rcs
