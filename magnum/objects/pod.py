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

from oslo_versionedobjects import fields

from magnum.common import exception
from magnum.common.pythonk8sclient.swagger_client import rest
from magnum.db import api as dbapi
from magnum.objects import base

import ast


@base.MagnumObjectRegistry.register
class Pod(base.MagnumPersistentObject, base.MagnumObject,
          base.MagnumObjectDictCompat):
    # Version 1.0: Initial version
    # Version 1.1: Remove unused Pod object API 'list_by_bay_uuid'
    VERSION = '1.1'

    dbapi = dbapi.get_instance()

    fields = {
        'id': fields.IntegerField(),
        'uuid': fields.StringField(nullable=True),
        'name': fields.StringField(nullable=True),
        'desc': fields.StringField(nullable=True),
        'project_id': fields.StringField(nullable=True),
        'user_id': fields.StringField(nullable=True),
        'bay_uuid': fields.StringField(nullable=True),
        'images': fields.ListOfStringsField(nullable=True),
        'labels': fields.DictOfStringsField(nullable=True),
        'status': fields.StringField(nullable=True),
        'manifest_url': fields.StringField(nullable=True),
        'manifest': fields.StringField(nullable=True),
        'host': fields.StringField(nullable=True),
    }

    @base.remotable_classmethod
    def get_by_uuid(cls, context, uuid, bay_uuid, k8s_api):
        """Find a pod based on pod uuid and the uuid for a bay.

        :param context: Security context
        :param uuid: the uuid of a pod.
        :param bay_uuid: the UUID of the Bay
        :param k8s_api: k8s API object

        :returns: a :class:`Pod` object.
        """
        try:
            resp = k8s_api.list_namespaced_pod(namespace='default')
        except rest.ApiException as err:
            raise exception.KubernetesAPIFailed(err=err)

        if resp is None:
            raise exception.PodListNotFound(bay_uuid=bay_uuid)

        pod = {}
        for pod_entry in resp.items:
            if pod_entry.metadata.uid == uuid:
                pod['uuid'] = pod_entry.metadata.uid
                pod['name'] = pod_entry.metadata.name
                pod['project_id'] = context.project_id
                pod['user_id'] = context.user_id
                pod['bay_uuid'] = bay_uuid
                pod['images'] = [c.image for c in pod_entry.spec.containers]
                if not pod_entry.metadata.labels:
                    pod['labels'] = {}
                else:
                    pod['labels'] = ast.literal_eval(pod_entry.metadata.labels)
                pod['status'] = pod_entry.status.phase
                pod['host'] = pod_entry.spec.node_name

                pod_obj = Pod(context, **pod)
                return pod_obj
        raise exception.PodNotFound(pod=uuid)

    @base.remotable_classmethod
    def get_by_name(cls, context, name, bay_uuid, k8s_api):
        """Find a pod based on pod name and the uuid for a bay.

        :param context: Security context
        :param name: the name of a pod.
        :param bay_uuid: the UUID of the Bay
        :param k8s_api: k8s API object

        :returns: a :class:`Pod` object.
        """
        try:
            resp = k8s_api.read_namespaced_pod(name=name,
                                               namespace='default')
        except rest.ApiException as err:
            raise exception.KubernetesAPIFailed(err=err)

        if resp is None:
            raise exception.PodNotFound(pod=name)

        pod = {}
        pod['uuid'] = resp.metadata.uid
        pod['name'] = resp.metadata.name
        pod['project_id'] = context.project_id
        pod['user_id'] = context.user_id
        pod['bay_uuid'] = bay_uuid
        pod['images'] = [c.image for c in resp.spec.containers]
        if not resp.metadata.labels:
            pod['labels'] = {}
        else:
            pod['labels'] = ast.literal_eval(resp.metadata.labels)
        pod['status'] = resp.status.phase
        pod['host'] = resp.spec.node_name

        pod_obj = Pod(context, **pod)
        return pod_obj
