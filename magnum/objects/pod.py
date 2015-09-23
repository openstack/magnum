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

from magnum.db import api as dbapi
from magnum.objects import base


@base.MagnumObjectRegistry.register
class Pod(base.MagnumPersistentObject, base.MagnumObject,
          base.MagnumObjectDictCompat):
    # Version 1.0: Initial version
    VERSION = '1.0'

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

    @staticmethod
    def _from_db_object(pod, db_pod):
        """Converts a database entity to a formal object."""
        for field in pod.fields:
            # ignore manifest_url as it was used for create pod
            if field == 'manifest_url':
                continue
            if field == 'manifest':
                continue
            pod[field] = db_pod[field]

        pod.obj_reset_changes()
        return pod

    @staticmethod
    def _from_db_object_list(db_objects, cls, context):
        """Converts a list of database entities to a list of formal objects."""
        return [Pod._from_db_object(cls(context), obj) for obj in db_objects]

    @base.remotable_classmethod
    def get_by_id(cls, context, pod_id):
        """Find a pod based on its integer id and return a Pod object.

        :param pod_id: the id of a pod.
        :returns: a :class:`Pod` object.
        """
        db_pod = cls.dbapi.get_pod_by_id(context, pod_id)
        pod = Pod._from_db_object(cls(context), db_pod)
        return pod

    @base.remotable_classmethod
    def get_by_uuid(cls, context, uuid):
        """Find a pod based on uuid and return a :class:`Pod` object.

        :param uuid: the uuid of a pod.
        :param context: Security context
        :returns: a :class:`Pod` object.
        """
        db_pod = cls.dbapi.get_pod_by_uuid(context, uuid)
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
    def list_by_bay_uuid(cls, context, bay_uuid):
        """Return a list of :class:`Pod` objects associated with a given bay.

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
        db_pods = cls.dbapi.get_pod_list(context, limit=limit,
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
            if field == 'manifest_url':
                continue
            if field == 'manifest':
                continue
            if self.obj_attr_is_set(field) and self[field] != current[field]:
                self[field] = current[field]
