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


class BayModel(base.MagnumObject):
    # Version 1.0: Initial version
    VERSION = '1.0'

    dbapi = dbapi.get_instance()

    fields = {
        'id': int,
        'uuid': obj_utils.str_or_none,
        'project_id': obj_utils.str_or_none,
        'user_id': obj_utils.str_or_none,
        'name': obj_utils.str_or_none,
        'image_id': obj_utils.str_or_none,
        'flavor_id': obj_utils.str_or_none,
        'master_flavor_id': obj_utils.str_or_none,
        'keypair_id': obj_utils.str_or_none,
        'dns_nameserver': obj_utils.str_or_none,
        'external_network_id': obj_utils.str_or_none,
        'fixed_network': obj_utils.str_or_none,
        'apiserver_port': obj_utils.int_or_none,
        'docker_volume_size': obj_utils.int_or_none,
        'ssh_authorized_key': obj_utils.str_or_none,
    }

    @staticmethod
    def _from_db_object(baymodel, db_baymodel):
        """Converts a database entity to a formal object."""
        for field in baymodel.fields:
            baymodel[field] = db_baymodel[field]

        baymodel.obj_reset_changes()
        return baymodel

    @staticmethod
    def _from_db_object_list(db_objects, cls, context):
        """Converts a list of database entities to a list of formal objects."""
        return [BayModel._from_db_object(cls(context), obj) for obj in
                db_objects]

    @base.remotable_classmethod
    def get(cls, context, baymodel_id):
        """Find a baymodel based on its id or uuid and return a BayModel object.

        :param baymodel_id: the id *or* uuid of a baymodel.
        :returns: a :class:`BayModel` object.
        """
        if utils.is_int_like(baymodel_id):
            return cls.get_by_id(context, baymodel_id)
        elif utils.is_uuid_like(baymodel_id):
            return cls.get_by_uuid(context, baymodel_id)
        else:
            raise exception.InvalidIdentity(identity=baymodel_id)

    @base.remotable_classmethod
    def get_by_id(cls, context, baymodel_id):
        """Find a baymodel based on its integer id and return a BayModel object.

        :param baymodel_id: the id of a baymodel.
        :returns: a :class:`BayModel` object.
        """
        db_baymodel = cls.dbapi.get_baymodel_by_id(context, baymodel_id)
        baymodel = BayModel._from_db_object(cls(context), db_baymodel)
        return baymodel

    @base.remotable_classmethod
    def get_by_uuid(cls, context, uuid):
        """Find a baymodel based on uuid and return a :class:`BayModel` object.

        :param uuid: the uuid of a baymodel.
        :param context: Security context
        :returns: a :class:`BayModel` object.
        """
        db_baymodel = cls.dbapi.get_baymodel_by_uuid(context, uuid)
        baymodel = BayModel._from_db_object(cls(context), db_baymodel)
        return baymodel

    @base.remotable_classmethod
    def get_by_name(cls, context, name):
        """Find a baymodel based on name and return a :class:`BayModel` object.

        :param name: the name of a baymodel.
        :param context: Security context
        :returns: a :class:`BayModel` object.
        """
        db_baymodel = cls.dbapi.get_baymodel_by_name(context, name)
        baymodel = BayModel._from_db_object(cls(context), db_baymodel)
        return baymodel

    @base.remotable_classmethod
    def list(cls, context, limit=None, marker=None,
             sort_key=None, sort_dir=None):
        """Return a list of BayModel objects.

        :param context: Security context.
        :param limit: maximum number of resources to return in a single result.
        :param marker: pagination marker for large data sets.
        :param sort_key: column to sort results by.
        :param sort_dir: direction to sort. "asc" or "desc".
        :returns: a list of :class:`BayModel` object.

        """
        db_baymodels = cls.dbapi.get_baymodel_list(context, limit=limit,
                                                   marker=marker,
                                                   sort_key=sort_key,
                                                   sort_dir=sort_dir)
        return BayModel._from_db_object_list(db_baymodels, cls, context)

    @base.remotable
    def create(self, context=None):
        """Create a BayModel record in the DB.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: BayModel(context)

        """
        values = self.obj_get_changes()
        db_baymodel = self.dbapi.create_baymodel(values)
        self._from_db_object(self, db_baymodel)

    @base.remotable
    def destroy(self, context=None):
        """Delete the BayModel from the DB.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: BayModel(context)
        """
        self.dbapi.destroy_baymodel(self.uuid)
        self.obj_reset_changes()

    @base.remotable
    def save(self, context=None):
        """Save updates to this BayModel.

        Updates will be made column by column based on the result
        of self.what_changed().

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: BayModel(context)
        """
        updates = self.obj_get_changes()
        self.dbapi.update_baymodel(self.uuid, updates)

        self.obj_reset_changes()

    @base.remotable
    def refresh(self, context=None):
        """Loads updates for this BayModel.

        Loads a baymodel with the same uuid from the database and
        checks for updated attributes. Updates are applied from
        the loaded baymodel column by column, if there are any updates.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: BayModel(context)
        """
        current = self.__class__.get_by_uuid(self._context, uuid=self.uuid)
        for field in self.fields:
            if (hasattr(self, base.get_attrname(field)) and
                self[field] != current[field]):
                self[field] = current[field]
