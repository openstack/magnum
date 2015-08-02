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
class Node(base.MagnumPersistentObject, base.MagnumObject,
           base.MagnumObjectDictCompat):
    # Version 1.0: Initial version
    VERSION = '1.0'

    dbapi = dbapi.get_instance()

    fields = {
        'id': fields.IntegerField(),
        'uuid': fields.StringField(nullable=True),
        'project_id': fields.StringField(nullable=True),
        'user_id': fields.StringField(nullable=True),
        'type': fields.StringField(nullable=True),
        'image_id': fields.StringField(nullable=True),
        'ironic_node_id': fields.StringField(nullable=True)
    }

    @staticmethod
    def _from_db_object(node, db_node):
        """Converts a database entity to a formal object."""
        for field in node.fields:
            node[field] = db_node[field]

        node.obj_reset_changes()
        return node

    @staticmethod
    def _from_db_object_list(db_objects, cls, context):
        """Converts a list of database entities to a list of formal objects."""
        return [Node._from_db_object(cls(context), obj) for obj in db_objects]

    @base.remotable_classmethod
    def get_by_id(cls, context, node_id):
        """Find a node based on its integer id and return a Node object.

        :param node_id: the id of a node.
        :returns: a :class:`Node` object.
        """
        db_node = cls.dbapi.get_node_by_id(context, node_id)
        node = Node._from_db_object(cls(context), db_node)
        return node

    @base.remotable_classmethod
    def get_by_uuid(cls, context, uuid):
        """Find a node based on uuid and return a :class:`Node` object.

        :param uuid: the uuid of a node.
        :param context: Security context
        :returns: a :class:`Node` object.
        """
        db_node = cls.dbapi.get_node_by_uuid(context, uuid)
        node = Node._from_db_object(cls(context), db_node)
        return node

    @base.remotable_classmethod
    def list(cls, context, limit=None, marker=None,
             sort_key=None, sort_dir=None):
        """Return a list of Node objects.

        :param context: Security context.
        :param limit: maximum number of resources to return in a single result.
        :param marker: pagination marker for large data sets.
        :param sort_key: column to sort results by.
        :param sort_dir: direction to sort. "asc" or "desc".
        :returns: a list of :class:`Node` object.

        """
        db_nodes = cls.dbapi.get_node_list(context, limit=limit,
                                           marker=marker,
                                           sort_key=sort_key,
                                           sort_dir=sort_dir)
        return Node._from_db_object_list(db_nodes, cls, context)

    @base.remotable
    def create(self, context=None):
        """Create a Node record in the DB.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: Node(context)

        """
        values = self.obj_get_changes()
        db_node = self.dbapi.create_node(values)
        self._from_db_object(self, db_node)

    @base.remotable
    def destroy(self, context=None):
        """Delete the Node from the DB.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: Node(context)
        """
        self.dbapi.destroy_node(self.uuid)
        self.obj_reset_changes()

    @base.remotable
    def save(self, context=None):
        """Save updates to this Node.

        Updates will be made column by column based on the result
        of self.what_changed().

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: Node(context)
        """
        updates = self.obj_get_changes()
        self.dbapi.update_node(self.uuid, updates)

        self.obj_reset_changes()

    @base.remotable
    def refresh(self, context=None):
        """Loads updates for this Node.

        Loads a node with the same uuid from the database and
        checks for updated attributes. Updates are applied from
        the loaded node column by column, if there are any updates.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: Node(context)
        """
        current = self.__class__.get_by_uuid(self._context, uuid=self.uuid)
        for field in self.fields:
            if self.obj_attr_is_set(field) and self[field] != current[field]:
                self[field] = current[field]
