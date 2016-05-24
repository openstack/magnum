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


from k8sclient.client import rest
from oslo_log import log as logging
from oslo_utils import uuidutils

from magnum.common import exception
from magnum.common import k8s_manifest
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

    # Replication Controller Operations
    def rc_create(self, context, rc):
        LOG.debug("rc_create")
        bay = conductor_utils.retrieve_bay(context, rc.bay_uuid)
        self.k8s_api = k8s.create_k8s_api(context, bay)
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
        bay = conductor_utils.retrieve_bay(context, bay_ident)
        self.k8s_api = k8s.create_k8s_api(context, bay)
        if uuidutils.is_uuid_like(rc_ident):
            rc = objects.ReplicationController.get_by_uuid(context, rc_ident,
                                                           bay.uuid,
                                                           self.k8s_api)
        else:
            rc = objects.ReplicationController.get_by_name(context, rc_ident,
                                                           bay.uuid,
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
        rc['bay_uuid'] = bay.uuid
        rc['labels'] = ast.literal_eval(resp.metadata.labels)
        rc['replicas'] = resp.status.replicas

        return rc

    def rc_delete(self, context, rc_ident, bay_ident):
        LOG.debug("rc_delete %s", rc_ident)
        bay = conductor_utils.retrieve_bay(context, bay_ident)
        self.k8s_api = k8s.create_k8s_api(context, bay)
        if uuidutils.is_uuid_like(rc_ident):
            rc = objects.ReplicationController.get_by_uuid(context, rc_ident,
                                                           bay.uuid,
                                                           self.k8s_api)
            rc_name = rc.name
        else:
            rc_name = rc_ident
        if conductor_utils.object_has_stack(context, bay.uuid):
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
        bay = conductor_utils.retrieve_bay(context, bay_ident)
        self.k8s_api = k8s.create_k8s_api(context, bay)
        if uuidutils.is_uuid_like(rc_ident):
            rc = objects.ReplicationController.get_by_uuid(context, rc_ident,
                                                           bay.uuid,
                                                           self.k8s_api)
        else:
            rc = objects.ReplicationController.get_by_name(context, rc_ident,
                                                           bay.uuid,
                                                           self.k8s_api)

        return rc

    def rc_list(self, context, bay_ident):
        bay = conductor_utils.retrieve_bay(context, bay_ident)
        self.k8s_api = k8s.create_k8s_api(context, bay)
        try:
            resp = self.k8s_api.list_namespaced_replication_controller(
                namespace='default')
        except rest.ApiException as err:
            raise exception.KubernetesAPIFailed(err=err)

        if resp is None:
            raise exception.ReplicationControllerListNotFound(
                bay_uuid=bay.uuid)

        rcs = []
        for entry in resp._items:
            rc = {}
            rc['uuid'] = entry.metadata.uid
            rc['name'] = entry.metadata.name
            rc['project_id'] = context.project_id
            rc['user_id'] = context.user_id
            rc['images'] = [
                c.image for c in entry.spec.template.spec.containers]
            rc['bay_uuid'] = bay.uuid
            # Convert string to dictionary
            rc['labels'] = ast.literal_eval(entry.metadata.labels)
            rc['replicas'] = entry.status.replicas

            rc_obj = objects.ReplicationController(context, **rc)
            rcs.append(rc_obj)

        return rcs
