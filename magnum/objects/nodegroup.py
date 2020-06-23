# Copyright (c) 2018 European Organization for Nuclear Research.
# All Rights Reserved.
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

from oslo_utils import strutils
from oslo_utils import uuidutils
from oslo_versionedobjects import fields

from magnum.db import api as dbapi
from magnum.objects import base
from magnum.objects import fields as m_fields


@base.MagnumObjectRegistry.register
class NodeGroup(base.MagnumPersistentObject, base.MagnumObject,
                base.MagnumObjectDictCompat):
    # Version 1.0: Initial version
    # Version 1.1: min_node_count defaults to 0

    VERSION = '1.1'

    dbapi = dbapi.get_instance()

    fields = {
        'id': fields.IntegerField(),
        'uuid': fields.UUIDField(),
        'name': fields.StringField(),
        'cluster_id': fields.StringField(),
        'project_id': fields.StringField(),
        'docker_volume_size': fields.IntegerField(nullable=True),
        'labels': fields.DictOfStringsField(nullable=True),
        'flavor_id': fields.StringField(nullable=True),
        'image_id': fields.StringField(nullable=True),
        'node_addresses': fields.ListOfStringsField(nullable=True),
        'node_count': fields.IntegerField(nullable=False, default=1),
        'role': fields.StringField(),
        'max_node_count': fields.IntegerField(nullable=True),
        'min_node_count': fields.IntegerField(nullable=False, default=0),
        'is_default': fields.BooleanField(default=False),
        'stack_id': fields.StringField(nullable=True),
        'status': m_fields.ClusterStatusField(nullable=True),
        'status_reason': fields.StringField(nullable=True),
        'version': fields.StringField(nullable=True),
    }

    @staticmethod
    def _from_db_object(nodegroup, db_nodegroup):
        """Converts a database entity to a formal object."""
        for field in nodegroup.fields:
            nodegroup[field] = db_nodegroup[field]

        nodegroup.obj_reset_changes()
        return nodegroup

    @staticmethod
    def _from_db_object_list(db_objects, cls, context):
        """Converts a list of database entities to a list of formal objects."""
        return [NodeGroup._from_db_object(cls(context), obj)
                for obj in db_objects]

    @base.remotable_classmethod
    def get(cls, context, cluster_id, nodegroup_id):
        """Find a nodegroup based on its id or uuid and return a NodeGroup.

        :param cluster_id: the of id a cluster.
        :param nodegroup_id: the id of a nodegroup.
        :param context: Security context
        :returns: a :class:`NodeGroup` object.
        """
        if strutils.is_int_like(nodegroup_id):
            return cls.get_by_id(context, cluster_id, nodegroup_id)
        elif uuidutils.is_uuid_like(nodegroup_id):
            return cls.get_by_uuid(context, cluster_id, nodegroup_id)
        else:
            return cls.get_by_name(context, cluster_id, nodegroup_id)

    @base.remotable_classmethod
    def get_by_id(cls, context, cluster, id_):
        """Find a nodegroup based on its integer id and return a NodeGroup.

        :param cluster: the id of a cluster.
        :param id_: the id of a nodegroup.
        :param context: Security context
        :returns: a :class:`NodeGroup` object.
        """
        db_nodegroup = cls.dbapi.get_nodegroup_by_id(context, cluster, id_)
        nodegroup = NodeGroup._from_db_object(cls(context), db_nodegroup)
        return nodegroup

    @base.remotable_classmethod
    def get_by_uuid(cls, context, cluster, uuid):
        """Find a nodegroup based on uuid and return a :class:`NodeGroup`.

        :param cluster: the id of a cluster.
        :param uuid: the uuid of a nodegroup.
        :param context: Security context
        :returns: a :class:`NodeGroup` object.
        """
        db_nodegroup = cls.dbapi.get_nodegroup_by_uuid(context, cluster, uuid)
        nodegroup = NodeGroup._from_db_object(cls(context), db_nodegroup)
        return nodegroup

    @base.remotable_classmethod
    def get_by_name(cls, context, cluster, name):
        """Find a nodegroup based on name and return a NodeGroup object.

        :param cluster: the id of a cluster.
        :param name: the logical name of a nodegroup.
        :param context: Security context
        :returns: a :class:`NodeGroup` object.
        """
        db_nodegroup = cls.dbapi.get_nodegroup_by_name(context, cluster, name)
        nodegroup = NodeGroup._from_db_object(cls(context), db_nodegroup)
        return nodegroup

    @base.remotable_classmethod
    def get_count_all(cls, context, cluster_id):
        """Get count of nodegroups in cluster.

        :param context: The security context
        :param cluster_id: The uuid of the cluster
        :returns: Count of nodegroups in the cluster.
        """
        return cls.dbapi.get_cluster_nodegroup_count(context, cluster_id)

    @base.remotable_classmethod
    def list(cls, context, cluster_id, limit=None, marker=None,
             sort_key=None, sort_dir=None, filters=None):
        """Return a list of NodeGroup objects.

        :param context: Security context.
        :param cluster: The cluster uuid or name
        :param limit: maximum number of resources to return in a single result.
        :param marker: pagination marker for large data sets.
        :param sort_key: column to sort results by.
        :param sort_dir: direction to sort. "asc" or "desc".
        :param filters: filter dict, can includes 'name', 'node_count',
                        'stack_id', 'node_addresses',
                        'status'(should be a status list).
        :returns: a list of :class:`NodeGroup` objects.

        """
        db_nodegroups = cls.dbapi.list_cluster_nodegroups(
            context, cluster_id, limit=limit, marker=marker, sort_key=sort_key,
            sort_dir=sort_dir, filters=filters)
        return NodeGroup._from_db_object_list(db_nodegroups, cls, context)

    @base.remotable
    def create(self, context=None):
        """Create a nodegroup record in the DB.

        :param context: Security context
        """
        values = self.obj_get_changes()
        db_nodegroup = self.dbapi.create_nodegroup(values)
        self._from_db_object(self, db_nodegroup)

    @base.remotable
    def destroy(self, context=None):
        """Delete the NodeGroup from the DB.

        :param context: Security context.
        """
        self.dbapi.destroy_nodegroup(self.cluster_id, self.uuid)
        self.obj_reset_changes()

    @base.remotable
    def save(self, context=None):
        """Save updates to this NodeGroup.

        Updates will be made column by column based on the result
        of self.what_changed().

        :param context: Security context.
        """
        updates = self.obj_get_changes()
        self.dbapi.update_nodegroup(self.cluster_id, self.uuid, updates)

        self.obj_reset_changes()

    @base.remotable
    def refresh(self, context=None):
        """Loads updates for this NodeGroup.

        Loads a NodeGroup with the same uuid from the database and
        checks for updated attributes. Updates are applied from
        the loaded NogeGroup column by column, if there are any updates.

        :param context: Security context.
        """
        current = self.__class__.get_by_uuid(self._context,
                                             cluster=self.cluster_id,
                                             uuid=self.uuid)
        for field in self.fields:
            if self.obj_attr_is_set(field) and self[field] != current[field]:
                self[field] = current[field]

    @base.remotable_classmethod
    def update_nodegroup(cls, context, cluster_id, nodegroup_id, values):
        """Updates a NodeGroup.

        :param context: Security context.
        :param cluster_id:
        :param nodegroup_id:
        :param values: a dictionary with the changed values
        """
        current = cls.get(context, cluster_id, nodegroup_id)
        db_nodegroup = cls.dbapi.update_nodegroup(cluster_id, current.uuid,
                                                  values)
        return NodeGroup._from_db_object(cls(context), db_nodegroup)
