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
class ClusterTemplate(base.MagnumPersistentObject, base.MagnumObject,
                      base.MagnumObjectDictCompat):
    # Version 1.0: Initial version
    # Version 1.1: Add 'registry_enabled' field
    # Version 1.2: Added 'network_driver' field
    # Version 1.3: Added 'labels' attribute
    # Version 1.4: Added 'insecure' attribute
    # Version 1.5: Changed type of 'coe' from StringField to BayTypeField
    # Version 1.6: Change 'insecure' to 'tls_disabled'
    # Version 1.7: Added 'public' field
    # Version 1.8: Added 'server_type' field
    # Version 1.9: Added 'volume_driver' field
    # Version 1.10: Removed 'ssh_authorized_key' field
    # Version 1.11: Added 'insecure_registry' field
    # Version 1.12: Added 'docker_storage_driver' field
    # Version 1.13: Added 'master_lb_enabled' field
    # Version 1.14: Added 'fixed_subnet' field
    # Version 1.15: Added 'floating_ip_enabled' field
    # Version 1.16: Renamed the class from "BayModel' to 'ClusterTemplate'
    # Version 1.17: 'coe' field type change to ClusterTypeField
    # Version 1.18: DockerStorageDriver is a StringField (was an Enum)
    # Version 1.19: Added 'hidden' field
    # Version 1.20: Added 'tags' field
    # Version 1.21: Added 'driver' field
    VERSION = '1.21'

    dbapi = dbapi.get_instance()

    fields = {
        'id': fields.IntegerField(),
        'uuid': fields.StringField(nullable=True),
        'project_id': fields.StringField(nullable=True),
        'user_id': fields.StringField(nullable=True),
        'name': fields.StringField(nullable=True),
        'image_id': fields.StringField(nullable=True),
        'flavor_id': fields.StringField(nullable=True),
        'master_flavor_id': fields.StringField(nullable=True),
        'keypair_id': fields.StringField(nullable=True),
        'dns_nameserver': fields.StringField(nullable=True),
        'external_network_id': fields.StringField(nullable=True),
        'fixed_network': fields.StringField(nullable=True),
        'fixed_subnet': fields.StringField(nullable=True),
        'network_driver': fields.StringField(nullable=True),
        'volume_driver': fields.StringField(nullable=True),
        'apiserver_port': fields.IntegerField(nullable=True),
        'docker_volume_size': fields.IntegerField(nullable=True),
        'docker_storage_driver': fields.StringField(nullable=True),
        'cluster_distro': fields.StringField(nullable=True),
        'coe': m_fields.ClusterTypeField(nullable=True),
        'http_proxy': fields.StringField(nullable=True),
        'https_proxy': fields.StringField(nullable=True),
        'no_proxy': fields.StringField(nullable=True),
        'registry_enabled': fields.BooleanField(default=False),
        'labels': fields.DictOfStringsField(nullable=True),
        'tls_disabled': fields.BooleanField(default=False),
        'public': fields.BooleanField(default=False),
        'server_type': fields.StringField(nullable=True),
        'insecure_registry': fields.StringField(nullable=True),
        'master_lb_enabled': fields.BooleanField(default=False),
        'floating_ip_enabled': fields.BooleanField(default=True),
        'hidden': fields.BooleanField(default=False),
        'tags': fields.StringField(nullable=True),
        'driver': fields.StringField(nullable=True),
    }

    @staticmethod
    def _from_db_object(cluster_template, db_cluster_template):
        """Converts a database entity to a formal object."""
        for field in cluster_template.fields:
            cluster_template[field] = db_cluster_template[field]

        cluster_template.obj_reset_changes()
        return cluster_template

    @staticmethod
    def _from_db_object_list(db_objects, cls, context):
        """Converts a list of database entities to a list of formal objects."""
        return [ClusterTemplate._from_db_object(cls(context), obj) for obj in
                db_objects]

    @base.remotable_classmethod
    def get(cls, context, cluster_template_id):
        """Find and return ClusterTemplate object based on its id or uuid.

        :param cluster_template_id: the id *or* uuid of a ClusterTemplate.
        :param context: Security context
        :returns: a :class:`ClusterTemplate` object.
        """
        if strutils.is_int_like(cluster_template_id):
            return cls.get_by_id(context, cluster_template_id)
        elif uuidutils.is_uuid_like(cluster_template_id):
            return cls.get_by_uuid(context, cluster_template_id)
        else:
            return cls.get_by_name(context, cluster_template_id)

    @base.remotable_classmethod
    def get_by_id(cls, context, cluster_template_id):
        """Find and return ClusterTemplate object based on its integer id.

        :param cluster_template_id: the id of a ClusterTemplate.
        :param context: Security context
        :returns: a :class:`ClusterTemplate` object.
        """
        db_cluster_template = cls.dbapi.get_cluster_template_by_id(
            context, cluster_template_id)
        cluster_template = ClusterTemplate._from_db_object(cls(context),
                                                           db_cluster_template)
        return cluster_template

    @base.remotable_classmethod
    def get_by_uuid(cls, context, uuid):
        """Find and return ClusterTemplate object based on uuid.

        :param uuid: the uuid of a ClusterTemplate.
        :param context: Security context
        :returns: a :class:`ClusterTemplate` object.
        """
        db_cluster_template = cls.dbapi.get_cluster_template_by_uuid(
            context, uuid)
        cluster_template = ClusterTemplate._from_db_object(cls(context),
                                                           db_cluster_template)
        return cluster_template

    @base.remotable_classmethod
    def get_by_name(cls, context, name):
        """Find and return ClusterTemplate object based on name.

        :param name: the name of a ClusterTemplate.
        :param context: Security context
        :returns: a :class:`ClusterTemplate` object.
        """
        db_cluster_template = cls.dbapi.get_cluster_template_by_name(context,
                                                                     name)
        cluster_template = ClusterTemplate._from_db_object(cls(context),
                                                           db_cluster_template)
        return cluster_template

    @base.remotable_classmethod
    def list(cls, context, limit=None, marker=None,
             sort_key=None, sort_dir=None):
        """Return a list of ClusterTemplate objects.

        :param context: Security context.
        :param limit: maximum number of resources to return in a single result.
        :param marker: pagination marker for large data sets.
        :param sort_key: column to sort results by.
        :param sort_dir: direction to sort. "asc" or "desc".
        :returns: a list of :class:`ClusterTemplate` object.

        """
        db_cluster_templates = cls.dbapi.get_cluster_template_list(
            context, limit=limit, marker=marker, sort_key=sort_key,
            sort_dir=sort_dir)
        return ClusterTemplate._from_db_object_list(db_cluster_templates,
                                                    cls, context)

    @base.remotable
    def create(self, context=None):
        """Create a ClusterTemplate record in the DB.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: ClusterTemplate(context)

        """
        values = self.obj_get_changes()
        db_cluster_template = self.dbapi.create_cluster_template(values)
        self._from_db_object(self, db_cluster_template)

    @base.remotable
    def destroy(self, context=None):
        """Delete the ClusterTemplate from the DB.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: ClusterTemplate(context)
        """
        self.dbapi.destroy_cluster_template(self.uuid)
        self.obj_reset_changes()

    @base.remotable
    def save(self, context=None):
        """Save updates to this ClusterTemplate.

        Updates will be made column by column based on the result
        of self.what_changed().

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: ClusterTemplate(context)
        """
        updates = self.obj_get_changes()
        self.dbapi.update_cluster_template(self.uuid, updates)

        self.obj_reset_changes()

    @base.remotable
    def refresh(self, context=None):
        """Loads updates for this ClusterTemplate.

        Loads a ClusterTemplate with the same uuid from the database and
        checks for updated attributes. Updates are applied from
        the loaded ClusterTemplate column by column, if there are any updates.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: ClusterTemplate(context)
        """
        current = self.__class__.get_by_uuid(self._context, uuid=self.uuid)
        for field in self.fields:
            if self.obj_attr_is_set(field) and self[field] != current[field]:
                self[field] = current[field]
