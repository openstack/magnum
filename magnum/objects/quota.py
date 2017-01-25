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
class Quota(base.MagnumPersistentObject, base.MagnumObject,
            base.MagnumObjectDictCompat):
    # Version 1.0: Initial version
    VERSION = '1.0'

    dbapi = dbapi.get_instance()

    fields = {
        'id': fields.IntegerField(),
        'project_id': fields.StringField(nullable=False),
        'resource': fields.StringField(nullable=False),
        'hard_limit': fields.IntegerField(nullable=False),
    }

    @base.remotable_classmethod
    def get_quota_by_project_id_resource(cls, context, project_id, resource):
        """Find a quota based on its integer id and return a Quota object.

        :param project_id: the id of a project.
        :param resource: resource name.
        :param context: Security context
        :returns: a :class:`Quota` object.
        """
        db_quota = cls.dbapi.get_quota_by_project_id_resource(project_id,
                                                              resource)
        quota = Quota._from_db_object(cls(context), db_quota)
        return quota

    @staticmethod
    def _from_db_object(quota, db_quota):
        """Converts a database entity to a formal object."""
        for field in quota.fields:
            setattr(quota, field, db_quota[field])

        quota.obj_reset_changes()
        return quota

    @staticmethod
    def _from_db_object_list(db_objects, cls, context):
        """Converts a list of database entities to a list of formal objects."""
        return [Quota._from_db_object(cls(context), obj)
                for obj in db_objects]

    @base.remotable_classmethod
    def get_by_id(cls, context, quota_id):
        """Find a quota based on its integer id and return a Quota object.

        :param quota_id: the id of a quota.
        :param context: Security context
        :returns: a :class:`Quota` object.
        """
        db_quota = cls.dbapi.get_quota_by_id(context, quota_id)
        quota = Quota._from_db_object(cls(context), db_quota)
        return quota

    @base.remotable_classmethod
    def list(cls, context, limit=None, marker=None,
             sort_key=None, sort_dir=None, filters=None):
        """Return a list of Quota objects.

        :param context: Security context.
        :param limit: maximum number of resources to return in a single result.
        :param marker: pagination marker for large data sets.
        :param sort_key: column to sort results by.
        :param sort_dir: direction to sort. "asc" or "desc".
        :param filters: filter dict, can includes 'project_id',
                        'resource'.
        :returns: a list of :class:`Quota` object.

        """
        db_quotas = cls.dbapi.get_quota_list(context,
                                             limit=limit,
                                             marker=marker,
                                             sort_key=sort_key,
                                             sort_dir=sort_dir,
                                             filters=filters)
        return Quota._from_db_object_list(db_quotas, cls, context)

    @base.remotable_classmethod
    def quota_get_all_by_project_id(cls, context, project_id):
        """Find a quota based on project id.

        :param project_id: the project id.
        :param context: Security context
        :returns: a :class:`Quota` object.
        """
        quotas = cls.dbapi.get_quota_by_project_id(context, project_id)
        return Quota._from_db_object_list(quotas, cls, context)

    @base.remotable
    def create(self, context=None):
        """Save a quota based on project id.

        :param context: security context.
        :returns: a :class:`Quota` object.
        """
        values = self.obj_get_changes()
        db_quota = self.dbapi.create_quota(values)
        self._from_db_object(self, db_quota)

    @base.remotable
    def delete(self, context=None):
        """Delete the quota from the DB.

        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: Quota(context)
        """
        self.dbapi.delete_quota(self.project_id, self.resource)
        self.obj_reset_changes()

    @base.remotable_classmethod
    def update_quota(cls, context, project_id, quota):
        """Save a quota based on project id.

        :param quota: quota.
        :returns: a :class:`Quota` object.
        """
        db_quota = cls.dbapi.update_quota(project_id, quota)
        return Quota._from_db_object(cls(context), db_quota)
