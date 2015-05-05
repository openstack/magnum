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

from oslo_versionedobjects import fields

from magnum.db import api as dbapi
from magnum.objects import base


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

    @staticmethod
    def _from_db_object(rc, db_rc):
        """Converts a database entity to a formal object."""
        for field in rc.fields:
            # ignore manifest_url as it was used for create rc
            if field == 'manifest_url':
                continue
            # ignore manifest as it was used for create rc
            if field == 'manifest':
                continue
            rc[field] = db_rc[field]

        rc.obj_reset_changes()
        return rc

    @staticmethod
    def _from_db_object_list(db_objects, cls, context):
        """Converts a list of database entities to a list of formal objects."""
        return [ReplicationController._from_db_object(cls(context), obj)
                for obj in db_objects]

    @base.remotable_classmethod
    def get_by_id(cls, context, rc_id):
        """Find a ReplicationController based on its integer id and return a
        ReplicationController object.

        :param rc_id: the id of a ReplicationController.
        :returns: a :class:`ReplicationController` object.
        """
        db_rc = cls.dbapi.get_rc_by_id(context, rc_id)
        rc = ReplicationController._from_db_object(cls(context), db_rc)
        return rc

    @base.remotable_classmethod
    def get_by_uuid(cls, context, uuid):
        """Find a ReplicationController based on uuid and return
        a :class:`ReplicationController` object.

        :param uuid: the uuid of a ReplicationController.
        :param context: Security context
        :returns: a :class:`ReplicationController` object.
        """
        db_rc = cls.dbapi.get_rc_by_uuid(context, uuid)
        rc = ReplicationController._from_db_object(cls(context), db_rc)
        return rc

    @base.remotable_classmethod
    def get_by_name(cls, context, name):
        """Find a ReplicationController based on name and return
        a :class:`ReplicationController` object.

        :param name: the name of a ReplicationController.
        :param context: Security context
        :returns: a :class:`ReplicationController` object.
        """
        db_rc = cls.dbapi.get_rc_by_name(name)
        rc = ReplicationController._from_db_object(cls(context), db_rc)
        return rc

    @base.remotable_classmethod
    def list(cls, context, limit=None, marker=None,
             sort_key=None, sort_dir=None):
        """Return a list of ReplicationController objects.

        :param context: Security context.
        :param limit: maximum number of resources to return in a single result.
        :param marker: pagination marker for large data sets.
        :param sort_key: column to sort results by.
        :param sort_dir: direction to sort. "asc" or "desc".
        :returns: a list of :class:`ReplicationController` object.

        """
        db_rcs = cls.dbapi.get_rc_list(context, limit=limit,
                                       marker=marker,
                                       sort_key=sort_key,
                                       sort_dir=sort_dir)
        return ReplicationController._from_db_object_list(db_rcs, cls, context)

    @base.remotable
    def create(self, context=None):
        """Create a ReplicationController record in the DB.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: ReplicationController(context)

        """
        values = self.obj_get_changes()
        db_rc = self.dbapi.create_rc(values)
        self._from_db_object(self, db_rc)

    @base.remotable
    def destroy(self, context=None):
        """Delete the ReplicationController from the DB.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: ReplicationController(context)
        """
        self.dbapi.destroy_rc(self.uuid)
        self.obj_reset_changes()

    @base.remotable
    def save(self, context=None):
        """Save updates to this ReplicationController.

        Updates will be made column by column based on the result
        of self.what_changed().

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: ReplicationController(context)
        """
        updates = self.obj_get_changes()
        self.dbapi.update_rc(self.uuid, updates)

        self.obj_reset_changes()

    @base.remotable
    def refresh(self, context=None):
        """Loads updates for this ReplicationController.

        Loads a rc with the same uuid from the database and
        checks for updated attributes. Updates are applied from
        the loaded rc column by column, if there are any updates.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: ReplicationController(context)
        """
        current = self.__class__.get_by_uuid(self._context, uuid=self.uuid)
        for field in self.fields:
            if field == 'manifest_url':
                continue
            if field == 'manifest':
                continue
            if self.obj_attr_is_set(field) and self[field] != current[field]:
                self[field] = current[field]
