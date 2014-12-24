# coding=utf-8
#
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

from magnum.common import exception
from magnum.common import utils
from magnum.db import api as dbapi
from magnum.objects import base
from magnum.objects import utils as obj_utils


class Pod(base.MagnumObject):
    # Version 1.0: Initial version
    VERSION = '1.0'

    dbapi = dbapi.get_instance()

    fields = {
        'id': int,
        'uuid': obj_utils.str_or_none,
        'name': obj_utils.str_or_none,
        'desc': obj_utils.str_or_none,
        'bay_uuid': obj_utils.str_or_none,
    }

    @staticmethod
    def _from_db_object(pod, db_pod):
        """Converts a database entity to a formal object."""
        for field in pod.fields:
            pod[field] = db_pod[field]

        pod.obj_reset_changes()
        return pod

    @staticmethod
    def _from_db_object_list(db_objects, cls, context):
        """Converts a list of database entities to a list of formal objects."""
        return [Pod._from_db_object(cls(context), obj) for obj in db_objects]

    @base.remotable_classmethod
    def get(cls, context, pod_id):
        """Find a pod based on its id or uuid and return a Pod object.

        :param pod_id: the id *or* uuid of a pod.
        :returns: a :class:`Pod` object.
        """
        if utils.is_int_like(pod_id):
            return cls.get_by_id(context, pod_id)
        elif utils.is_uuid_like(pod_id):
            return cls.get_by_uuid(context, pod_id)
        else:
            raise exception.InvalidIdentity(identity=pod_id)

    @base.remotable_classmethod
    def get_by_id(cls, context, pod_id):
        """Find a pod based on its integer id and return a Pod object.

        :param pod_id: the id of a pod.
        :returns: a :class:`Pod` object.
        """
        db_pod = cls.dbapi.get_pod_by_id(pod_id)
        pod = Pod._from_db_object(cls(context), db_pod)
        return pod

    @base.remotable_classmethod
    def get_by_uuid(cls, context, uuid):
        """Find a pod based on uuid and return a :class:`Pod` object.

        :param uuid: the uuid of a pod.
        :param context: Security context
        :returns: a :class:`Pod` object.
        """
        db_pod = cls.dbapi.get_pod_by_uuid(uuid)
        pod = Pod._from_db_object(cls(context), db_pod)
        return pod

    @base.remotable_classmethod
    def get_by_name(cls, context, name):
        """Find a pod based on pod name and return a :class:`Pod` object.

        :param name: the name of a pod.
        :param context: Security context
        :returns: a :class:`Pod` object.
        """
        db_pod = cls.dbapi.get_pod_by_name(name)
        pod = Pod._from_db_object(cls(context), db_pod)
        return pod

    @base.remotable_classmethod
    def get_by_bay_uuid(cls, context, bay_uuid):
        """Find a pods based on bay uuid and return a :class:`Pod` object.

        :param bay_uuid: the uuid of a bay.
        :param context: Security context
        :returns: a list of class:`Pod` object.
        """
        db_pods = cls.dbapi.get_pods_by_bay_uuid(bay_uuid)
        return Pod._from_db_object_list(db_pods, cls, context)

    @base.remotable_classmethod
    def list(cls, context, limit=None, marker=None,
             sort_key=None, sort_dir=None):
        """Return a list of Pod objects.

        :param context: Security context.
        :param limit: maximum number of resources to return in a single result.
        :param marker: pagination marker for large data sets.
        :param sort_key: column to sort results by.
        :param sort_dir: direction to sort. "asc" or "desc".
        :returns: a list of :class:`Pod` object.

        """
        db_pods = cls.dbapi.get_pod_list(limit=limit,
                                         marker=marker,
                                         sort_key=sort_key,
                                         sort_dir=sort_dir)
        return Pod._from_db_object_list(db_pods, cls, context)

    @base.remotable
    def create(self, context=None):
        """Create a Pod record in the DB.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: Pod(context)

        """
        values = self.obj_get_changes()
        db_pod = self.dbapi.create_pod(values)
        self._from_db_object(self, db_pod)

    @base.remotable
    def destroy(self, context=None):
        """Delete the Pod from the DB.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: Pod(context)
        """
        self.dbapi.destroy_pod(self.uuid)
        self.obj_reset_changes()

    @base.remotable
    def save(self, context=None):
        """Save updates to this Pod.

        Updates will be made column by column based on the result
        of self.what_changed().

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: Pod(context)
        """
        updates = self.obj_get_changes()
        self.dbapi.update_pod(self.uuid, updates)

        self.obj_reset_changes()

    @base.remotable
    def refresh(self, context=None):
        """Loads updates for this Pod.

        Loads a pod with the same uuid from the database and
        checks for updated attributes. Updates are applied from
        the loaded pod column by column, if there are any updates.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: Pod(context)
        """
        current = self.__class__.get_by_uuid(self._context, uuid=self.uuid)
        for field in self.fields:
            if (hasattr(self, base.get_attrname(field)) and
                    self[field] != current[field]):
                self[field] = current[field]
