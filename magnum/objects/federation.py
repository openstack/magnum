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

from oslo_utils import strutils
from oslo_utils import uuidutils
from oslo_versionedobjects import fields

from magnum.common import exception
from magnum.db import api as dbapi
from magnum.objects import base
from magnum.objects import fields as m_fields


@base.MagnumObjectRegistry.register
class Federation(base.MagnumPersistentObject, base.MagnumObject,
                 base.MagnumObjectDictCompat):
    """Represents a Federation object.

    Version 1.0: Initial Version
    """

    VERSION = '1.0'

    dbapi = dbapi.get_instance()

    fields = {
        'id': fields.IntegerField(),
        'uuid': fields.UUIDField(nullable=True),
        'name': fields.StringField(nullable=True),
        'project_id': fields.StringField(nullable=True),
        'hostcluster_id': fields.StringField(nullable=True),
        'member_ids': fields.ListOfStringsField(nullable=True),
        'status': m_fields.FederationStatusField(nullable=True),
        'status_reason': fields.StringField(nullable=True),
        'properties': fields.DictOfStringsField(nullable=True)
    }

    @staticmethod
    def _from_db_object(federation, db_federation):
        """Converts a database entity to a formal object."""
        for field in federation.fields:
            federation[field] = db_federation[field]

        federation.obj_reset_changes()
        return federation

    @staticmethod
    def _from_db_object_list(db_objects, cls, context):
        """Converts a list of database entities to a list of formal objects."""
        return [Federation._from_db_object(cls(context), obj)
                for obj in db_objects]

    @base.remotable_classmethod
    def get(cls, context, federation_id):
        """Find a federation based on its id or uuid and return it.

        :param federation_id: the id *or* uuid of a federation.
        :param context: Security context
        :returns: a :class:`Federation` object.
        """
        if strutils.is_int_like(federation_id):
            return cls.get_by_id(context, federation_id)
        elif uuidutils.is_uuid_like(federation_id):
            return cls.get_by_uuid(context, federation_id)
        else:
            raise exception.InvalidIdentity(identity=federation_id)

    @base.remotable_classmethod
    def get_by_id(cls, context, federation_id):
        """Find a federation based on its integer id and return it.

        :param federation_id: the id of a federation.
        :param context: Security context
        :returns: a :class:`Federation` object.
        """
        db_federation = cls.dbapi.get_federation_by_id(context, federation_id)
        federation = Federation._from_db_object(cls(context), db_federation)
        return federation

    @base.remotable_classmethod
    def get_by_uuid(cls, context, uuid):
        """Find a federation based on uuid and return it.

        :param uuid: the uuid of a federation.
        :param context: Security context
        :returns: a :class:`Federation` object.
        """
        db_federation = cls.dbapi.get_federation_by_uuid(context, uuid)
        federation = Federation._from_db_object(cls(context), db_federation)
        return federation

    @base.remotable_classmethod
    def get_count_all(cls, context, filters=None):
        """Get count of matching federation.

        :param context: The security context
        :param filters: filter dict, can includes 'name', 'project_id',
                        'hostcluster_id', 'member_ids', 'status' (should be a
                        status list).
        :returns: Count of matching federation.
        """
        return cls.dbapi.get_federation_count_all(context, filters=filters)

    @base.remotable_classmethod
    def get_by_name(cls, context, name):
        """Find a federation based on name and return a Federation object.

        :param name: the logical name of a federation.
        :param context: Security context
        :returns: a :class:`Federation` object.
        """
        db_federation = cls.dbapi.get_federation_by_name(context, name)
        federation = Federation._from_db_object(cls(context), db_federation)
        return federation

    @base.remotable_classmethod
    def list(cls, context, limit=None, marker=None,
             sort_key=None, sort_dir=None, filters=None):
        """Return a list of Federation objects.

        :param context: Security context.
        :param limit: maximum number of resources to return in a single result.
        :param marker: pagination marker for large data sets.
        :param sort_key: column to sort results by.
        :param sort_dir: direction to sort. "asc" or "desc".
        :param filters: filter dict, can includes 'name', 'project_id',
                        'hostcluster_id', 'member_ids', 'status' (should be a
                        status list).
        :returns: a list of :class:`Federation` object.

        """
        db_federation = cls.dbapi.get_federation_list(context, limit=limit,
                                                      marker=marker,
                                                      sort_key=sort_key,
                                                      sort_dir=sort_dir,
                                                      filters=filters)
        return Federation._from_db_object_list(db_federation, cls, context)

    @base.remotable
    def create(self, context=None):
        """Create a Federation record in the DB.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: Federation(context)

        """
        values = self.obj_get_changes()
        db_federation = self.dbapi.create_federation(values)
        self._from_db_object(self, db_federation)

    @base.remotable
    def destroy(self, context=None):
        """Delete the Federation from the DB.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: Federation(context)
        """
        self.dbapi.destroy_federation(self.uuid)
        self.obj_reset_changes()

    @base.remotable
    def save(self, context=None):
        """Save updates to this Federation.

        Updates will be made column by column based on the result
        of self.what_changed().

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: Federation(context)
        """
        updates = self.obj_get_changes()
        self.dbapi.update_federation(self.uuid, updates)

        self.obj_reset_changes()

    @base.remotable
    def refresh(self, context=None):
        """Load updates for this Federation.

        Loads a Federation with the same uuid from the database and
        checks for updated attributes. Updates are applied from
        the loaded Federation column by column, if there are any updates.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: Federation(context)
        """
        current = self.__class__.get_by_uuid(self._context, uuid=self.uuid)
        for field in self.fields:
            if self.obj_attr_is_set(field) and self[field] != current[field]:
                self[field] = current[field]
