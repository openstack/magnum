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
from magnum.objects.cluster_template import ClusterTemplate
from magnum.objects import fields as m_fields


@base.MagnumObjectRegistry.register
class Cluster(base.MagnumPersistentObject, base.MagnumObject,
              base.MagnumObjectDictCompat):
    # Version 1.0: Initial version
    # Version 1.1: Added 'bay_create_timeout' field
    # Version 1.2: Add 'registry_trust_id' field
    # Version 1.3: Added 'baymodel' field
    # Version 1.4: Added more types of status to bay's status field
    # Version 1.5: Rename 'registry_trust_id' to 'trust_id'
    #              Add 'trustee_user_name', 'trustee_password',
    #              'trustee_user_id' field
    # Version 1.6: Add rollback support for Bay
    # Version 1.7: Added 'coe_version'  and 'container_version' fields
    # Version 1.8: Rename 'baymodel' to 'cluster_template'
    # Version 1.9: Rename table name from 'bay' to 'cluster'
    #              Rename 'baymodel_id' to 'cluster_template_id'
    #              Rename 'bay_create_timeout' to 'create_timeout'
    # Version 1.10: Added 'keypair' field
    # Version 1.11: Added 'RESUME_FAILED' in status field
    # Version 1.12: Added 'get_stats' method
    # Version 1.13: Added get_count_all method
    # Version 1.14: Added 'docker_volume_size' field
    # Version 1.15: Added 'labels' field
    # Version 1.16: Added 'master_flavor_id' field
    # Version 1.17: Added 'flavor_id' field
    # Version 1.18: Added 'health_status' and 'health_status_reason' field

    VERSION = '1.18'

    dbapi = dbapi.get_instance()

    fields = {
        'id': fields.IntegerField(),
        'uuid': fields.UUIDField(nullable=True),
        'name': fields.StringField(nullable=True),
        'project_id': fields.StringField(nullable=True),
        'user_id': fields.StringField(nullable=True),
        'cluster_template_id': fields.StringField(nullable=True),
        'keypair': fields.StringField(nullable=True),
        'docker_volume_size': fields.IntegerField(nullable=True),
        'labels': fields.DictOfStringsField(nullable=True),
        'master_flavor_id': fields.StringField(nullable=True),
        'flavor_id': fields.StringField(nullable=True),
        'stack_id': fields.StringField(nullable=True),
        'status': m_fields.ClusterStatusField(nullable=True),
        'status_reason': fields.StringField(nullable=True),
        'health_status': m_fields.ClusterHealthStatusField(nullable=True),
        'health_status_reason': fields.DictOfStringsField(nullable=True),
        'create_timeout': fields.IntegerField(nullable=True),
        'api_address': fields.StringField(nullable=True),
        'node_addresses': fields.ListOfStringsField(nullable=True),
        'node_count': fields.IntegerField(nullable=True),
        'master_count': fields.IntegerField(nullable=True),
        'discovery_url': fields.StringField(nullable=True),
        'master_addresses': fields.ListOfStringsField(nullable=True),
        'ca_cert_ref': fields.StringField(nullable=True),
        'magnum_cert_ref': fields.StringField(nullable=True),
        'cluster_template': fields.ObjectField('ClusterTemplate'),
        'trust_id': fields.StringField(nullable=True),
        'trustee_username': fields.StringField(nullable=True),
        'trustee_password': fields.StringField(nullable=True),
        'trustee_user_id': fields.StringField(nullable=True),
        'coe_version': fields.StringField(nullable=True),
        'container_version': fields.StringField(nullable=True)
    }

    @staticmethod
    def _from_db_object(cluster, db_cluster):
        """Converts a database entity to a formal object."""
        for field in cluster.fields:
            if field != 'cluster_template':
                cluster[field] = db_cluster[field]

        # Note(eliqiao): The following line needs to be placed outside the
        # loop because there is a dependency from cluster_template to
        # cluster_template_id. The cluster_template_id must be populated
        # first in the loop before it can be used to find the cluster_template.
        cluster['cluster_template'] = ClusterTemplate.get_by_uuid(
            cluster._context, cluster.cluster_template_id)

        cluster.obj_reset_changes()
        return cluster

    @staticmethod
    def _from_db_object_list(db_objects, cls, context):
        """Converts a list of database entities to a list of formal objects."""
        return [Cluster._from_db_object(cls(context), obj)
                for obj in db_objects]

    @base.remotable_classmethod
    def get(cls, context, cluster_id):
        """Find a cluster based on its id or uuid and return a Cluster object.

        :param cluster_id: the id *or* uuid of a cluster.
        :param context: Security context
        :returns: a :class:`Cluster` object.
        """
        if strutils.is_int_like(cluster_id):
            return cls.get_by_id(context, cluster_id)
        elif uuidutils.is_uuid_like(cluster_id):
            return cls.get_by_uuid(context, cluster_id)
        else:
            raise exception.InvalidIdentity(identity=cluster_id)

    @base.remotable_classmethod
    def get_by_id(cls, context, cluster_id):
        """Find a cluster based on its integer id and return a Cluster object.

        :param cluster_id: the id of a cluster.
        :param context: Security context
        :returns: a :class:`Cluster` object.
        """
        db_cluster = cls.dbapi.get_cluster_by_id(context, cluster_id)
        cluster = Cluster._from_db_object(cls(context), db_cluster)
        return cluster

    @base.remotable_classmethod
    def get_by_uuid(cls, context, uuid):
        """Find a cluster based on uuid and return a :class:`Cluster` object.

        :param uuid: the uuid of a cluster.
        :param context: Security context
        :returns: a :class:`Cluster` object.
        """
        db_cluster = cls.dbapi.get_cluster_by_uuid(context, uuid)
        cluster = Cluster._from_db_object(cls(context), db_cluster)
        return cluster

    @base.remotable_classmethod
    def get_count_all(cls, context, filters=None):
        """Get count of matching clusters.

        :param context: The security context
        :param filters: filter dict, can includes 'cluster_template_id',
                        'name', 'node_count', 'stack_id', 'api_address',
                        'node_addresses', 'project_id', 'user_id',
                        'status'(should be a status list), 'master_count'.
        :returns: Count of matching clusters.
        """
        return cls.dbapi.get_cluster_count_all(context, filters=filters)

    @base.remotable_classmethod
    def get_by_name(cls, context, name):
        """Find a cluster based on name and return a Cluster object.

        :param name: the logical name of a cluster.
        :param context: Security context
        :returns: a :class:`Cluster` object.
        """
        db_cluster = cls.dbapi.get_cluster_by_name(context, name)
        cluster = Cluster._from_db_object(cls(context), db_cluster)
        return cluster

    @base.remotable_classmethod
    def list(cls, context, limit=None, marker=None,
             sort_key=None, sort_dir=None, filters=None):
        """Return a list of Cluster objects.

        :param context: Security context.
        :param limit: maximum number of resources to return in a single result.
        :param marker: pagination marker for large data sets.
        :param sort_key: column to sort results by.
        :param sort_dir: direction to sort. "asc" or "desc".
        :param filters: filter dict, can includes 'cluster_template_id',
                        'name', 'node_count', 'stack_id', 'api_address',
                        'node_addresses', 'project_id', 'user_id',
                        'status'(should be a status list), 'master_count'.
        :returns: a list of :class:`Cluster` object.

        """
        db_clusters = cls.dbapi.get_cluster_list(context, limit=limit,
                                                 marker=marker,
                                                 sort_key=sort_key,
                                                 sort_dir=sort_dir,
                                                 filters=filters)
        return Cluster._from_db_object_list(db_clusters, cls, context)

    @base.remotable_classmethod
    def get_stats(cls, context, project_id=None):
        """Return a list of Cluster objects.

        :param context: Security context.
        :param project_id: project id
        """
        return cls.dbapi.get_cluster_stats(project_id)

    @base.remotable
    def create(self, context=None):
        """Create a Cluster record in the DB.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: Cluster(context)

        """
        values = self.obj_get_changes()
        db_cluster = self.dbapi.create_cluster(values)
        self._from_db_object(self, db_cluster)

    @base.remotable
    def destroy(self, context=None):
        """Delete the Cluster from the DB.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: Cluster(context)
        """
        self.dbapi.destroy_cluster(self.uuid)
        self.obj_reset_changes()

    @base.remotable
    def save(self, context=None):
        """Save updates to this Cluster.

        Updates will be made column by column based on the result
        of self.what_changed().

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: Cluster(context)
        """
        updates = self.obj_get_changes()
        self.dbapi.update_cluster(self.uuid, updates)

        self.obj_reset_changes()

    @base.remotable
    def refresh(self, context=None):
        """Loads updates for this Cluster.

        Loads a Cluster with the same uuid from the database and
        checks for updated attributes. Updates are applied from
        the loaded Cluster column by column, if there are any updates.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: Cluster(context)
        """
        current = self.__class__.get_by_uuid(self._context, uuid=self.uuid)
        for field in self.fields:
            if self.obj_attr_is_set(field) and self[field] != current[field]:
                self[field] = current[field]
