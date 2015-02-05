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

from magnum.db import api as dbapi
from magnum.objects import base
from magnum.objects import utils as obj_utils


class ReplicationController(base.MagnumObject):
    # Version 1.0: Initial version
    VERSION = '1.0'

    dbapi = dbapi.get_instance()

    fields = {
        'id': int,
        'uuid': obj_utils.str_or_none,
        'name': obj_utils.str_or_none,
        'project_id': obj_utils.str_or_none,
        'user_id': obj_utils.str_or_none,
        'images': obj_utils.list_or_none,
        'bay_uuid': obj_utils.str_or_none,
        'labels': obj_utils.dict_or_none,
        'replicas': obj_utils.int_or_none,
        'manifest_url': obj_utils.str_or_none,
        'manifest': obj_utils.str_or_none,
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
        return [ReplicationController._from_db_object(cls(context),
                                                    obj) for obj in db_objects]

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
            if (hasattr(self, base.get_attrname(field)) and
                    self[field] != current[field]):
                self[field] = current[field]
