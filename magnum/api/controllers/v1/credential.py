#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

import pecan
from wsme import types as wtypes

from oslo_log import log

from magnum.api.controllers import base
from magnum.api.controllers.v1 import types
from magnum.api import expose
from magnum.api import utils as api_utils
from magnum.common import policy


LOG = log.getLogger(__name__)


class ClusterID(wtypes.Base):
    """API representation of a cluster ID

    This class enforces type checking and value constraints, and converts
    between the internal object model and the API representation of a cluster
    ID.
    """

    uuid = types.uuid
    """Unique UUID for this cluster"""

    def __init__(self, uuid):
        self.uuid = uuid


class CredentialsController(base.Controller):
    """REST controller for cluster actions."""
    def __init__(self):
        super(CredentialsController, self).__init__()

    @base.Controller.api_version("1.12")
    @expose.expose(ClusterID, types.uuid_or_name, status_code=202)
    def patch(self, cluster_ident):
        """Rotate the credential in use by a cluster.

        :param cluster_ident: UUID of a cluster or logical name of the cluster.
        """

        context = pecan.request.context
        policy.enforce(context, 'credential:rotate',
                       action='credential:rotate')

        cluster = api_utils.get_resource('Cluster', cluster_ident)
        # NOTE(northcottmt): Perform rotation synchronously as there aren't any
        # slow apply/upgrade operations to do
        pecan.request.rpcapi.credential_rotate(cluster)

        return ClusterID(cluster.uuid)
