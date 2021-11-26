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
from magnum.objects.nodegroup import NodeGroup


LAZY_LOADED_ATTRS = ['cluster_template']


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
    # Version 1.19: Added nodegroups, default_ng_worker, default_ng_master
    # Version 1.20: Fields node_count, master_count, node_addresses,
    #               master_addresses are now properties.
    # Version 1.21  Added fixed_network, fixed_subnet, floating_ip_enabled
    # Version 1.22  Added master_lb_enabled
    # Version 1.23  Added etcd_ca_cert_ref and front_proxy_ca_cert_ref

    VERSION = '1.23'

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
        'discovery_url': fields.StringField(nullable=True),
        'ca_cert_ref': fields.StringField(nullable=True),
        'magnum_cert_ref': fields.StringField(nullable=True),
        'etcd_ca_cert_ref': fields.StringField(nullable=True),
        'front_proxy_ca_cert_ref': fields.StringField(nullable=True),
        'cluster_template': fields.ObjectField('ClusterTemplate'),
        'trust_id': fields.StringField(nullable=True),
        'trustee_username': fields.StringField(nullable=True),
        'trustee_password': fields.StringField(nullable=True),
        'trustee_user_id': fields.StringField(nullable=True),
        'coe_version': fields.StringField(nullable=True),
        'container_version': fields.StringField(nullable=True),
        'fixed_network': fields.StringField(nullable=True),
        'fixed_subnet': fields.StringField(nullable=True),
        'floating_ip_enabled': fields.BooleanField(default=True),
        'master_lb_enabled': fields.BooleanField(default=False),
    }

    @staticmethod
    def _from_db_object(cluster, db_cluster):
        """Converts a database entity to a formal object."""
        for field in cluster.fields:
            # cluster_template will be loaded lazily when it is needed
            # by obj_load_attr.
            if field != 'cluster_template':
                cluster[field] = db_cluster[field]

        cluster.obj_reset_changes()
        return cluster

    @property
    def nodegroups(self):
        # Returns all nodegroups that belong to the cluster.
        return NodeGroup.list(self._context, self.uuid)

    @property
    def default_ng_worker(self):
        # Assume that every cluster will have only one default
        # non-master nodegroup. We don't want to limit the roles
        # so each nodegroup that does not have a master role is
        # considered as a worker/minion nodegroup.
        filters = {'is_default': True}
        default_ngs = NodeGroup.list(self._context, self.uuid, filters=filters)
        return [n for n in default_ngs if n.role != 'master'][0]

    @property
    def default_ng_master(self):
        # Assume that every cluster will have only one default
        # master nodegroup.
        filters = {'role': 'master', 'is_default': True}
        return NodeGroup.list(self._context, self.uuid, filters=filters)[0]

    @property
    def node_count(self):
        return sum(n.node_count for n in self.nodegroups if n.role != 'master')

    @property
    def master_count(self):
        return sum(n.node_count for n in self.nodegroups if n.role == 'master')

    @property
    def node_addresses(self):
        node_addresses = []
        for ng in self.nodegroups:
            if ng.role != 'master':
                node_addresses += ng.node_addresses
        return node_addresses

    @property
    def master_addresses(self):
        master_addresses = []
        for ng in self.nodegroups:
            if ng.role == 'master':
                master_addresses += ng.node_addresses
        return master_addresses

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

    def obj_load_attr(self, attrname):
        if attrname not in LAZY_LOADED_ATTRS:
            raise exception.ObjectError(
                action='obj_load_attr', obj_name=self.name, obj_id=self.uuid,
                reason='unable to lazy-load %s' % attrname)

        self['cluster_template'] = ClusterTemplate.get_by_uuid(
            self._context, self.cluster_template_id)

        self.obj_reset_changes(['cluster_template'])

    def as_dict(self):
        dict_ = super(Cluster, self).as_dict()
        # Update the dict with the attributes coming form
        # the cluster's nodegroups.
        dict_.update({
            'node_count': self.node_count,
            'master_count': self.master_count,
            'node_addresses': self.node_addresses,
            'master_addresses': self.master_addresses
        })
        return dict_
