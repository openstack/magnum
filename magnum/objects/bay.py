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


class Status(object):
    CREATE_IN_PROGRESS = 'CREATE_IN_PROGRESS'
    CREATE_FAILED = 'CREATE_FAILED'
    CREATED = 'CREATED'
    UPDATE_IN_PROGRESS = 'UPDATE_IN_PROGRESS'
    UPDATE_FAILED = 'UPDATE_FAILED'
    UPDATED = 'UPDATED'
    DELETE_IN_PROGRESS = 'DELETE_IN_PROGRESS'
    DELETE_FAILED = 'DELETE_FAILED'
    DELETED = 'DELETED'


class Bay(base.MagnumObject):
    # Version 1.0: Initial version
    VERSION = '1.0'

    dbapi = dbapi.get_instance()

    fields = {
        'id': int,
        'uuid': obj_utils.str_or_none,
        'name': obj_utils.str_or_none,
        'project_id': obj_utils.str_or_none,
        'user_id': obj_utils.str_or_none,
        'baymodel_id': obj_utils.str_or_none,
        'stack_id': obj_utils.str_or_none,
        # One of CREATE_IN_PROGRESS|CREATE_FAILED|CREATED
        #        UPDATE_IN_PROGRESS|UPDATE_FAILED|UPDATED
        #        DELETE_IN_PROGRESS|DELETE_FAILED|DELETED
        'status': obj_utils.str_or_none,
        'api_address': obj_utils.str_or_none,
        'node_addresses': obj_utils.list_or_none,
        'node_count': obj_utils.int_or_none
    }

    @staticmethod
    def _from_db_object(bay, db_bay):
        """Converts a database entity to a formal object."""
        for field in bay.fields:
            bay[field] = db_bay[field]

        bay.obj_reset_changes()
        return bay

    @staticmethod
    def _from_db_object_list(db_objects, cls, context):
        """Converts a list of database entities to a list of formal objects."""
        return [Bay._from_db_object(cls(context), obj) for obj in db_objects]

    @base.remotable_classmethod
    def get(cls, context, bay_id):
        """Find a bay based on its id or uuid and return a Bay object.

        :param bay_id: the id *or* uuid of a bay.
        :returns: a :class:`Bay` object.
        """
        if utils.is_int_like(bay_id):
            return cls.get_by_id(context, bay_id)
        elif utils.is_uuid_like(bay_id):
            return cls.get_by_uuid(context, bay_id)
        else:
            raise exception.InvalidIdentity(identity=bay_id)

    @base.remotable_classmethod
    def get_by_id(cls, context, bay_id):
        """Find a bay based on its integer id and return a Bay object.

        :param bay_id: the id of a bay.
        :returns: a :class:`Bay` object.
        """
        db_bay = cls.dbapi.get_bay_by_id(context, bay_id)
        bay = Bay._from_db_object(cls(context), db_bay)
        return bay

    @base.remotable_classmethod
    def get_by_uuid(cls, context, uuid):
        """Find a bay based on uuid and return a :class:`Bay` object.

        :param uuid: the uuid of a bay.
        :param context: Security context
        :returns: a :class:`Bay` object.
        """
        db_bay = cls.dbapi.get_bay_by_uuid(context, uuid)
        bay = Bay._from_db_object(cls(context), db_bay)
        return bay

    @base.remotable_classmethod
    def get_by_name(cls, context, name):
        """Find a bay based on name and return a Bay object.

        :param name: the logical name of a bay.
        :param context: Security context
        :returns: a :class:`Bay` object.
        """
        db_bay = cls.dbapi.get_bay_by_name(context, name)
        bay = Bay._from_db_object(cls(context), db_bay)
        return bay

    @base.remotable_classmethod
    def list(cls, context, limit=None, marker=None,
             sort_key=None, sort_dir=None):
        """Return a list of Bay objects.

        :param context: Security context.
        :param limit: maximum number of resources to return in a single result.
        :param marker: pagination marker for large data sets.
        :param sort_key: column to sort results by.
        :param sort_dir: direction to sort. "asc" or "desc".
        :returns: a list of :class:`Bay` object.

        """
        db_bays = cls.dbapi.get_bay_list(context, limit=limit,
                                         marker=marker,
                                         sort_key=sort_key,
                                         sort_dir=sort_dir)
        return Bay._from_db_object_list(db_bays, cls, context)

    @base.remotable
    def create(self, context=None):
        """Create a Bay record in the DB.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: Bay(context)

        """
        values = self.obj_get_changes()
        db_bay = self.dbapi.create_bay(values)
        self._from_db_object(self, db_bay)

    @base.remotable
    def destroy(self, context=None):
        """Delete the Bay from the DB.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: Bay(context)
        """
        self.dbapi.destroy_bay(self.uuid)
        self.obj_reset_changes()

    @base.remotable
    def save(self, context=None):
        """Save updates to this Bay.

        Updates will be made column by column based on the result
        of self.what_changed().

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: Bay(context)
        """
        updates = self.obj_get_changes()
        self.dbapi.update_bay(self.uuid, updates)

        self.obj_reset_changes()

    @base.remotable
    def refresh(self, context=None):
        """Loads updates for this Bay.

        Loads a bay with the same uuid from the database and
        checks for updated attributes. Updates are applied from
        the loaded bay column by column, if there are any updates.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: Bay(context)
        """
        current = self.__class__.get_by_uuid(self._context, uuid=self.uuid)
        for field in self.fields:
            if (hasattr(self, base.get_attrname(field)) and
                self[field] != current[field]):
                self[field] = current[field]
