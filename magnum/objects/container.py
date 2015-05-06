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

from oslo_versionedobjects import fields

from magnum.db import api as dbapi
from magnum.objects import base


# possible status
ERROR = 'Error'
RUNNING = 'Running'
STOPPED = 'Stopped'
PAUSED = 'Paused'


@base.MagnumObjectRegistry.register
class Container(base.MagnumPersistentObject, base.MagnumObject,
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
        'image_id': fields.StringField(nullable=True),
        'command': fields.StringField(nullable=True),
        'bay_uuid': fields.StringField(nullable=True),
        'status': fields.StringField(nullable=True),
    }

    @staticmethod
    def _from_db_object(container, db_container):
        """Converts a database entity to a formal object."""
        for field in container.fields:
            container[field] = db_container[field]

        container.obj_reset_changes()
        return container

    @staticmethod
    def _from_db_object_list(db_objects, cls, context):
        """Converts a list of database entities to a list of formal objects."""
        return [Container._from_db_object(cls(context), obj)
                for obj in db_objects]

    @base.remotable_classmethod
    def get_by_id(cls, context, container_id):
        """Find a container based on its integer id and return a Container object.

        :param container_id: the id of a container.
        :returns: a :class:`Container` object.
        """
        db_container = cls.dbapi.get_container_by_id(context, container_id)
        container = Container._from_db_object(cls(context), db_container)
        return container

    @base.remotable_classmethod
    def get_by_uuid(cls, context, uuid):
        """Find a container based on uuid and return a :class:`Container` object.

        :param uuid: the uuid of a container.
        :param context: Security context
        :returns: a :class:`Container` object.
        """
        db_container = cls.dbapi.get_container_by_uuid(context, uuid)
        container = Container._from_db_object(cls(context), db_container)
        return container

    @base.remotable_classmethod
    def get_by_name(cls, context, name):
        """Find a bay based on name and return a Bay object.

        :param name: the logical name of a bay.
        :param context: Security context
        :returns: a :class:`Bay` object.
        """
        db_bay = cls.dbapi.get_container_by_name(context, name)
        bay = Container._from_db_object(cls(context), db_bay)
        return bay

    @base.remotable_classmethod
    def list(cls, context, limit=None, marker=None,
             sort_key=None, sort_dir=None):
        """Return a list of Container objects.

        :param context: Security context.
        :param limit: maximum number of resources to return in a single result.
        :param marker: pagination marker for large data sets.
        :param sort_key: column to sort results by.
        :param sort_dir: direction to sort. "asc" or "desc".
        :returns: a list of :class:`Container` object.

        """
        db_containers = cls.dbapi.get_container_list(context, limit=limit,
                                                     marker=marker,
                                                     sort_key=sort_key,
                                                     sort_dir=sort_dir)
        return Container._from_db_object_list(db_containers, cls, context)

    @base.remotable
    def create(self, context=None):
        """Create a Container record in the DB.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: Container(context)

        """
        values = self.obj_get_changes()
        db_container = self.dbapi.create_container(values)
        self._from_db_object(self, db_container)

    @base.remotable
    def destroy(self, context=None):
        """Delete the Container from the DB.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: Container(context)
        """
        self.dbapi.destroy_container(self.uuid)
        self.obj_reset_changes()

    @base.remotable
    def save(self, context=None):
        """Save updates to this Container.

        Updates will be made column by column based on the result
        of self.what_changed().

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: Container(context)
        """
        updates = self.obj_get_changes()
        self.dbapi.update_container(self.uuid, updates)

        self.obj_reset_changes()

    @base.remotable
    def refresh(self, context=None):
        """Loads updates for this Container.

        Loads a container with the same uuid from the database and
        checks for updated attributes. Updates are applied from
        the loaded container column by column, if there are any updates.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: Container(context)
        """
        current = self.__class__.get_by_uuid(self._context, uuid=self.uuid)
        for field in self.fields:
            if self.obj_attr_is_set(field) and self[field] != current[field]:
                self[field] = current[field]
