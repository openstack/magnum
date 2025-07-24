# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from oslo_log import log as logging

from magnum.common import exception
from magnum.common import profiler
import magnum.conf
from magnum.drivers.common import driver
from magnum.i18n import _
from magnum.objects import fields

CONF = magnum.conf.CONF

LOG = logging.getLogger(__name__)

ALLOWED_CLUSTER_STATES = {
    fields.ClusterStatus.CREATE_COMPLETE,
    fields.ClusterStatus.UPDATE_COMPLETE,
    fields.ClusterStatus.UPDATE_IN_PROGRESS,
    fields.ClusterStatus.UPDATE_FAILED,
    fields.ClusterStatus.RESUME_COMPLETE,
    fields.ClusterStatus.RESTORE_COMPLETE,
    fields.ClusterStatus.ROLLBACK_COMPLETE,
    fields.ClusterStatus.SNAPSHOT_COMPLETE,
    fields.ClusterStatus.CHECK_COMPLETE,
    fields.ClusterStatus.ADOPT_COMPLETE
}


@profiler.trace_cls("rpc")
class Handler(object):

    def __init__(self):
        super(Handler, self).__init__()

    def credential_rotate(self, context, cluster):
        if cluster.status not in ALLOWED_CLUSTER_STATES:
            operation = _(
                f'{__name__} when cluster status is "{cluster.status}"')
            raise exception.NotSupported(operation=operation)

        cluster_driver = driver.Driver.get_driver_for_cluster(context, cluster)

        try:
            cluster_driver.rotate_credential(context, cluster)
        except NotImplementedError:
            raise exception.NotSupported(
                message=_("Credential rotation is not supported by driver."))
