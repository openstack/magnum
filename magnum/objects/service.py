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


class Service(base.MagnumObject):
    # Version 1.0: Initial version
    VERSION = '1.0'

    dbapi = dbapi.get_instance()

    fields = {
        'id': int,
        'uuid': obj_utils.str_or_none,
        'name': obj_utils.str_or_none,
        'bay_uuid': obj_utils.str_or_none,
        'labels': obj_utils.dict_or_none,
        'selector': obj_utils.dict_or_none,
        'ip': obj_utils.str_or_none,
        'port': int,
        'service_definition_url': obj_utils.str_or_none,
        'service_data': obj_utils.str_or_none,
    }

    @staticmethod
    def _from_db_object(service, db_service):
        """Converts a database entity to a formal object."""
        for field in service.fields:
            # ignore service_definition_url as it was used for create service
            if field == 'service_definition_url':
                continue
            if field == 'service_data':
                continue
            service[field] = db_service[field]

        service.obj_reset_changes()
        return service

    @staticmethod
    def _from_db_object_list(db_objects, cls, context):
        """Converts a list of database entities to a list of formal objects."""
        return [Service._from_db_object(cls(context), obj)
                for obj in db_objects]

    @base.remotable_classmethod
    def get(cls, context, service_id):
        """Find a service based on its id or uuid and return a Service object.

        :param service_id: the id *or* uuid of a service.
        :returns: a :class:`Service` object.
        """
        if utils.is_int_like(service_id):
            return cls.get_by_id(context, service_id)
        elif utils.is_uuid_like(service_id):
            return cls.get_by_uuid(context, service_id)
        else:
            raise exception.InvalidIdentity(identity=service_id)

    @base.remotable_classmethod
    def get_by_id(cls, context, service_id):
        """Find a service based on its integer id and return a Service object.

        :param service_id: the id of a service.
        :returns: a :class:`Service` object.
        """
        db_service = cls.dbapi.get_service_by_id(service_id)
        service = Service._from_db_object(cls(context), db_service)
        return service

    @base.remotable_classmethod
    def get_by_uuid(cls, context, uuid):
        """Find a service based on uuid and return a :class:`Service` object.

        :param uuid: the uuid of a service.
        :param context: Security context
        :returns: a :class:`Service` object.
        """
        db_service = cls.dbapi.get_service_by_uuid(uuid)
        service = Service._from_db_object(cls(context), db_service)
        return service

    @base.remotable_classmethod
    def list_by_bay_uuid(cls, context, bay_uuid):
        """Return a list of :class:`Service` objects associated with a given bay.

        :param bay_uuid: the uuid of a bay.
        :param context: Security context
        :returns: a list of class:`Service` object.
        """
        db_services = cls.dbapi.get_services_by_bay_uuid(bay_uuid)
        return Service._from_db_object_list(db_services, cls, context)

    @base.remotable_classmethod
    def list(cls, context, limit=None, marker=None,
             sort_key=None, sort_dir=None):
        """Return a list of Service objects.

        :param context: Security context.
        :param limit: maximum number of resources to return in a single result.
        :param marker: pagination marker for large data sets.
        :param sort_key: column to sort results by.
        :param sort_dir: direction to sort. "asc" or "desc".
        :returns: a list of :class:`Service` object.

        """
        db_services = cls.dbapi.get_service_list(limit=limit,
                                                 marker=marker,
                                                 sort_key=sort_key,
                                                 sort_dir=sort_dir)
        return Service._from_db_object_list(db_services, cls, context)

    @base.remotable
    def create(self, context=None):
        """Create a Service record in the DB.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: Service(context)

        """
        values = self.obj_get_changes()
        db_service = self.dbapi.create_service(values)
        self._from_db_object(self, db_service)

    @base.remotable
    def destroy(self, context=None):
        """Delete the Service from the DB.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: Service(context)
        """
        self.dbapi.destroy_service(self.uuid)
        self.obj_reset_changes()

    @base.remotable
    def save(self, context=None):
        """Save updates to this Service.

        Updates will be made column by column based on the result
        of self.what_changed().

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: Service(context)
        """
        updates = self.obj_get_changes()
        self.dbapi.update_service(self.uuid, updates)

        self.obj_reset_changes()

    @base.remotable
    def refresh(self, context=None):
        """Loads updates for this Service.

        Loads a service with the same uuid from the database and
        checks for updated attributes. Updates are applied from
        the loaded service column by column, if there are any updates.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: Service(context)
        """
        current = self.__class__.get_by_uuid(self._context, uuid=self.uuid)
        for field in self.fields:
            if (hasattr(self, base.get_attrname(field)) and
                    self[field] != current[field]):
                self[field] = current[field]
