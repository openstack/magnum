# Copyright 2013 UnitedStack Inc.
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

import pecan
import wsme
from wsme import types as wtypes

from magnum.api.controllers import base
from magnum.api.controllers.v1 import collection
from magnum.api.controllers.v1 import types
from magnum.api import expose
from magnum.api import utils as api_utils
from magnum.api import validation
from magnum.common import exception
from magnum.common import policy
import magnum.conf
from magnum.i18n import _
from magnum import objects
from magnum.objects import fields

CONF = magnum.conf.CONF


class Quota(base.APIBase):
    """API representation of a project Quota.

    This class enforces type checking and value constraints, and converts
    between the internal object model and the API representation of Quota.
    """
    id = wsme.wsattr(wtypes.IntegerType(minimum=1))
    """unique id"""

    hard_limit = wsme.wsattr(wtypes.IntegerType(minimum=0), default=1)
    """The hard limit for total number of clusters. Default to 1 if not set"""

    project_id = wsme.wsattr(wtypes.StringType(min_length=1, max_length=255),
                             default=None)
    """The project id"""

    resource = wsme.wsattr(wtypes.Enum(wtypes.text,
                                       *fields.QuotaResourceName.ALL),
                           default='Cluster')
    """The resource name"""

    def __init__(self, **kwargs):
        super(Quota, self).__init__()
        self.fields = []
        for field in objects.Quota.fields:
            # Skip fields we do not expose.
            if not hasattr(self, field):
                continue
            self.fields.append(field)
            setattr(self, field, kwargs.get(field, wtypes.Unset))

    @classmethod
    def convert(cls, quota):
        return Quota(**quota.as_dict())


class QuotaCollection(collection.Collection):
    """API representation of a collection of quotas."""

    quotas = [Quota]
    """A list containing quota objects"""

    def __init__(self, **kwargs):
        self._type = 'quotas'

    @staticmethod
    def convert(quotas, limit, **kwargs):
        collection = QuotaCollection()
        collection.quotas = [Quota.convert(p) for p in quotas]
        collection.next = collection.get_next(limit,
                                              marker_attribute='id',
                                              **kwargs)
        return collection


class QuotaController(base.Controller):
    """REST controller for Quotas."""

    def __init__(self):
        super(QuotaController, self).__init__()

    _custom_actions = {
        'detail': ['GET'],
    }

    def _get_quota_collection(self, marker, limit, sort_key, sort_dir,
                              filters):

        limit = api_utils.validate_limit(limit)
        sort_dir = api_utils.validate_sort_dir(sort_dir)

        marker_obj = None
        if marker:
            marker_obj = objects.Quota.get_by_id(pecan.request.context,
                                                 marker)

        quotas = objects.Quota.list(pecan.request.context,
                                    limit,
                                    marker_obj,
                                    sort_key=sort_key,
                                    sort_dir=sort_dir,
                                    filters=filters)

        return QuotaCollection.convert(quotas,
                                       limit,
                                       sort_key=sort_key,
                                       sort_dir=sort_dir)

    @expose.expose(QuotaCollection, int, int, wtypes.text, wtypes.text,
                   types.boolean)
    def get_all(self, marker=None, limit=None, sort_key='id',
                sort_dir='asc', all_tenants=False):
        """Retrieve a list of quotas.

        :param marker: pagination marker for large data sets.
        :param limit: maximum number of resources to return in a single result.
        :param sort_key: column to sort results by. Default: id.
        :param sort_dir: direction to sort. "asc" or "desc". Default: asc.
        :param all_tenants: a flag to indicate all or current tenant.
        """
        context = pecan.request.context
        policy.enforce(context, 'quota:get_all',
                       action='quota:get_all')

        filters = {}
        if not context.is_admin or not all_tenants:
            filters = {"project_id": context.project_id}

        return self._get_quota_collection(marker,
                                          limit,
                                          sort_key,
                                          sort_dir,
                                          filters)

    @expose.expose(Quota, wtypes.text, wtypes.text)
    def get_one(self, project_id, resource):
        """Retrieve Quota information for the given project_id.

        :param id: project id.
        :param resource: resource name.
        """
        context = pecan.request.context
        policy.enforce(context, 'quota:get', action='quota:get')

        if not context.is_admin and project_id != context.project_id:
            raise exception.NotAuthorized()

        try:
            quota = objects.Quota.get_quota_by_project_id_resource(context,
                                                                   project_id,
                                                                   resource)
            quota = Quota.convert(quota)
        except exception.QuotaNotFound:
            # If explicit quota was not set for the project, use default limit
            quota = Quota(project_id=project_id,
                          hard_limit=CONF.quotas.max_clusters_per_project)
        return quota

    @expose.expose(Quota, body=Quota, status_code=201)
    @validation.enforce_valid_project_id_on_create()
    def post(self, quota):
        """Create Quota.

        :param quota: a json document to create this Quota.
        """

        context = pecan.request.context
        policy.enforce(context, 'quota:create', action='quota:create')

        quota_dict = quota.as_dict()
        if 'project_id'not in quota_dict or not quota_dict['project_id']:
            msg = _('Must provide a valid project ID.')
            raise exception.InvalidParameterValue(message=msg)

        new_quota = objects.Quota(context, **quota_dict)
        new_quota.create()
        return Quota.convert(new_quota)

    @expose.expose(Quota, wtypes.text, wtypes.text, body=Quota,
                   status_code=202)
    def patch(self, project_id,  resource, quotapatch):
        """Update Quota for a given project_id.

        :param project_id: project id.
        :param resource: resource name.
        :param quotapatch: a json document to update Quota.
        """

        context = pecan.request.context
        policy.enforce(context, 'quota:update', action='quota:update')
        quota_dict = quotapatch.as_dict()
        quota_dict['project_id'] = project_id
        quota_dict['resource'] = resource
        db_quota = objects.Quota.update_quota(context, project_id, quota_dict)
        return Quota.convert(db_quota)

    @expose.expose(None, wtypes.text, wtypes.text, status_code=204)
    def delete(self, project_id,  resource):
        """Delete Quota for a given project_id and resource.

        :param project_id: project id.
        :param resource: resource name.
        """

        context = pecan.request.context
        policy.enforce(context, 'quota:delete', action='quota:delete')
        quota_dict = {"project_id": project_id, "resource": resource}
        quota = objects.Quota(context, **quota_dict)
        quota.delete()
