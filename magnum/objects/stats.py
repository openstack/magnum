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


@base.MagnumObjectRegistry.register
class Stats(base.MagnumObject, base.MagnumObjectDictCompat):
    # Version 1.0: Initial version

    VERSION = '1.0'

    dbapi = dbapi.get_instance()

    fields = {
        'clusters': fields.IntegerField(),
        'nodes': fields.IntegerField(nullable=True)
    }

    @base.remotable_classmethod
    def get_cluster_stats(cls, context, project_id=None):
        """Return cluster stats for the given project.

        :param context: The security context
        :param project_id: project id
        """
        clusters, nodes = cls.dbapi.get_cluster_stats(context, project_id)
        return cls(clusters=clusters, nodes=nodes)
