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
from wsme import types as wtypes

from magnum.api.controllers import base
from magnum.api import expose
from magnum.common import exception
from magnum.common import policy
from magnum.i18n import _
from magnum import objects


class Stats(base.APIBase):

    clusters = wtypes.IntegerType(minimum=0)
    nodes = wtypes.IntegerType(minimum=0)

    def __init__(self, **kwargs):
        self.fields = []
        for field in objects.Stats.fields:
            # Skip fields we do not expose.
            if not hasattr(self, field):
                continue
            self.fields.append(field)
            setattr(self, field, kwargs.get(field, wtypes.Unset))

    @classmethod
    def convert(cls, rpc_stats):
        return Stats(**rpc_stats.as_dict())


class StatsController(base.Controller):
    """REST controller for Stats."""
    def __init__(self, **kwargs):
        super(StatsController, self).__init__()

    @expose.expose(Stats, wtypes.text, wtypes.text)
    def get_all(self, project_id=None, type="cluster"):
        """Retrieve magnum stats.

        """
        context = pecan.request.context
        policy.enforce(context, 'stats:get_all', action='stats:get_all')
        allowed_stats = ["cluster"]

        if type.lower() not in allowed_stats:
            msg = _("Invalid stats type. Allowed values are '%s'")
            allowed_str = ','.join(allowed_stats)
            raise exception.InvalidParameterValue(err=msg % allowed_str)

        # 1.If the requester is not an admin and trying to request stats for
        # different tenant, then reject the request
        # 2.If the requester is not an admin and project_id was not provided,
        # then return self stats
        if not context.is_admin:
            project_id = project_id if project_id else context.project_id
            if project_id != context.project_id:
                raise exception.NotAuthorized()

        stats = objects.Stats.get_cluster_stats(context, project_id)
        return Stats.convert(stats)
