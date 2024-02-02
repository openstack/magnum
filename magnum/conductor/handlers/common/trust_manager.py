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
from magnum.common import utils

LOG = logging.getLogger(__name__)


def create_trustee_and_trust(osc, cluster):
    try:
        password = utils.generate_password(length=18)

        trustee = osc.keystone().create_trustee(
            "%s_%s" % (cluster.uuid, cluster.project_id),
            password,
        )

        cluster.trustee_username = trustee.name
        cluster.trustee_user_id = trustee.id
        cluster.trustee_password = password

        trust = osc.keystone().create_trust(
            cluster.trustee_user_id)
        cluster.trust_id = trust.id

    except Exception:
        LOG.exception(
            'Failed to create trustee and trust for Cluster: %s',
            cluster.uuid)
        raise exception.TrusteeOrTrustToClusterFailed(
            cluster_uuid=cluster.uuid)


def delete_trustee_and_trust(osc, context, cluster):
    try:
        kst = osc.keystone()

        # The cluster which is upgraded from Liberty doesn't have trust_id
        if cluster.trust_id:
            kst.delete_trust(context, cluster)
    except Exception:
        # Exceptions are already logged by keystone().delete_trust
        pass
    try:
        # The cluster which is upgraded from Liberty doesn't have
        # trustee_user_id
        if cluster.trustee_user_id:
            osc.keystone().delete_trustee(cluster.trustee_user_id)
    except Exception:
        # Exceptions are already logged by keystone().delete_trustee
        pass
