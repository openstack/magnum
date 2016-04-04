# Copyright 2015 IBM Corp.
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

import ast

from k8sclient.client import rest
from oslo_versionedobjects import fields

from magnum.common import exception
from magnum.db import api as dbapi
from magnum.objects import base


@base.MagnumObjectRegistry.register
class ReplicationController(base.MagnumPersistentObject, base.MagnumObject,
                            base.MagnumObjectDictCompat):
    # Version 1.0: Initial version
    VERSION = '1.0'

    dbapi = dbapi.get_instance()

    fields = {
        'id': fields.IntegerField(),
        'uuid': fields.StringField(nullable=True),
        'name': fields.StringField(nullable=True),
        'project_id': fields.StringField(nullable=True),
        'user_id': fields.StringField(nullable=True),
        'images': fields.ListOfStringsField(nullable=True),
        'bay_uuid': fields.StringField(nullable=True),
        'labels': fields.DictOfStringsField(nullable=True),
        'replicas': fields.IntegerField(nullable=True),
        'manifest_url': fields.StringField(nullable=True),
        'manifest': fields.StringField(nullable=True),
    }

    @base.remotable_classmethod
    def get_by_uuid(cls, context, uuid, bay_uuid, k8s_api):
        """Return a :class:`ReplicationController` object based on uuid.

        :param context: Security context
        :param uuid: the uuid of a ReplicationController.
        :param bay_uuid: the UUID of the Bay.

        :returns: a :class:`ReplicationController` object.
        """
        try:
            resp = k8s_api.list_namespaced_replication_controller(
                namespace='default')
        except rest.ApiException as err:
            raise exception.KubernetesAPIFailed(err=err)

        if resp is None:
            raise exception.ReplicationControllerListNotFound(
                bay_uuid=bay_uuid)

        rc = {}
        for entry in resp.items:
            if entry.metadata.uid == uuid:
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

                rc_obj = ReplicationController(context, **rc)
                return rc_obj

        raise exception.ReplicationControllerNotFound(rc=uuid)

    @base.remotable_classmethod
    def get_by_name(cls, context, name, bay_uuid, k8s_api):
        """Return a :class:`ReplicationController` object based on name.

        :param context: Security context
        :param name: the name of a ReplicationController.
        :param bay_uuid: the UUID of the Bay.

        :returns: a :class:`ReplicationController` object.
        """
        try:
            resp = k8s_api.read_namespaced_replication_controller(
                name=name,
                namespace='default')
        except rest.ApiException as err:
            raise exception.KubernetesAPIFailed(err=err)

        if resp is None:
            raise exception.ReplicationControllerNotFound(rc=name)

        rc = {}
        rc['uuid'] = resp.metadata.uid
        rc['name'] = resp.metadata.name
        rc['project_id'] = context.project_id
        rc['user_id'] = context.user_id
        rc['images'] = [c.image for c in resp.spec.template.spec.containers]
        rc['bay_uuid'] = bay_uuid
        # Convert string to dictionary
        rc['labels'] = ast.literal_eval(resp.metadata.labels)
        rc['replicas'] = resp.status.replicas

        rc_obj = ReplicationController(context, **rc)
        return rc_obj
