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


@base.MagnumObjectRegistry.register
class X509KeyPair(base.MagnumPersistentObject, base.MagnumObject):
    # Version 1.0: Initial version
    # Version 1.1: Added new method get_x509keypair_by_bay_uuid
    # Version 1.2: Remove bay_uuid, name, ca_cert and add intermediates
    #              and private_key_passphrase
    VERSION = '1.2'

    dbapi = dbapi.get_instance()

    fields = {
        'id': fields.IntegerField(),
        'uuid': fields.UUIDField(nullable=True),
        'certificate': fields.StringField(nullable=True),
        'private_key': fields.StringField(nullable=True),
        'intermediates': fields.StringField(nullable=True),
        'private_key_passphrase': fields.StringField(nullable=True),
        'project_id': fields.StringField(nullable=True),
        'user_id': fields.StringField(nullable=True),
    }

    @staticmethod
    def _from_db_object(x509keypair, db_x509keypair):
        """Converts a database entity to a formal object."""
        for field in x509keypair.fields:
            setattr(x509keypair, field, db_x509keypair[field])

        x509keypair.obj_reset_changes()
        return x509keypair

    @staticmethod
    def _from_db_object_list(db_objects, cls, context):
        """Converts a list of database entities to a list of formal objects."""
        return [X509KeyPair._from_db_object(cls(context), obj)
                for obj in db_objects]

    @base.remotable_classmethod
    def get(cls, context, x509keypair_id):
        """Find a X509KeyPair based on its id or uuid.

        Find X509KeyPair by id or uuid and return a X509KeyPair object.

        :param x509keypair_id: the id *or* uuid of a x509keypair.
        :param context: Security context
        :returns: a :class:`X509KeyPair` object.
        """
        if strutils.is_int_like(x509keypair_id):
            return cls.get_by_id(context, x509keypair_id)
        elif uuidutils.is_uuid_like(x509keypair_id):
            return cls.get_by_uuid(context, x509keypair_id)
        else:
            raise exception.InvalidIdentity(identity=x509keypair_id)

    @base.remotable_classmethod
    def get_by_id(cls, context, x509keypair_id):
        """Find a X509KeyPair based on its integer id.

        Find X509KeyPair by id and return a X509KeyPair object.

        :param x509keypair_id: the id of a x509keypair.
        :param context: Security context
        :returns: a :class:`X509KeyPair` object.
        """
        db_x509keypair = cls.dbapi.get_x509keypair_by_id(context,
                                                         x509keypair_id)
        x509keypair = X509KeyPair._from_db_object(cls(context), db_x509keypair)
        return x509keypair

    @base.remotable_classmethod
    def get_by_uuid(cls, context, uuid):
        """Find a x509keypair based on uuid and return a :class:`X509KeyPair` object.

        :param uuid: the uuid of a x509keypair.
        :param context: Security context
        :returns: a :class:`X509KeyPair` object.
        """  # noqa: E501
        db_x509keypair = cls.dbapi.get_x509keypair_by_uuid(context, uuid)
        x509keypair = X509KeyPair._from_db_object(cls(context), db_x509keypair)
        return x509keypair

    @base.remotable_classmethod
    def list(cls, context, limit=None, marker=None,
             sort_key=None, sort_dir=None, filters=None):
        """Return a list of X509KeyPair objects.

        :param context: Security context.
        :param limit: maximum number of resources to return in a single result.
        :param marker: pagination marker for large data sets.
        :param sort_key: column to sort results by.
        :param sort_dir: direction to sort. "asc" or "desc".
        :param filters: filter dict, can include 'x509keypairmodel_id',
                        'project_id', 'user_id'.
        :returns: a list of :class:`X509KeyPair` object.

        """
        db_x509keypairs = cls.dbapi.get_x509keypair_list(context, limit=limit,
                                                         marker=marker,
                                                         sort_key=sort_key,
                                                         sort_dir=sort_dir,
                                                         filters=filters)
        return X509KeyPair._from_db_object_list(db_x509keypairs, cls, context)

    @base.remotable
    def create(self, context=None):
        """Create a X509KeyPair record in the DB.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: X509KeyPair(context)

        """
        values = self.obj_get_changes()
        db_x509keypair = self.dbapi.create_x509keypair(values)
        self._from_db_object(self, db_x509keypair)

    @base.remotable
    def destroy(self, context=None):
        """Delete the X509KeyPair from the DB.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: X509KeyPair(context)
        """
        self.dbapi.destroy_x509keypair(self.uuid)
        self.obj_reset_changes()

    @base.remotable
    def save(self, context=None):
        """Save updates to this X509KeyPair.

        Updates will be made column by column based on the result
        of self.what_changed().

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: X509KeyPair(context)
        """
        updates = self.obj_get_changes()
        self.dbapi.update_x509keypair(self.uuid, updates)

        self.obj_reset_changes()

    @base.remotable
    def refresh(self, context=None):
        """Loads updates for this X509KeyPair.

        Loads a x509keypair with the same uuid from the database and
        checks for updated attributes. Updates are applied from
        the loaded x509keypair column by column, if there are any updates.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: X509KeyPair(context)
        """
        current = self.__class__.get_by_uuid(self._context, uuid=self.uuid)
        for field in self.fields:
            if self.obj_attr_is_set(field) and \
               getattr(self, field) != getattr(current, field):
                setattr(self, field, getattr(current, field))
