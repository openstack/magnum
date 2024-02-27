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
    kst = osc.keystone()
    try:
        if cluster.trust_id:
            kst.delete_trust(context, cluster)
            cluster.trust_id = None
    except Exception:
        # Exceptions are already logged by keystone().delete_trust
        pass
    try:
        if cluster.trustee_user_id:
            kst.delete_trustee(cluster.trustee_user_id)
            cluster.trustee_user_id = None
            cluster.trustee_username = None
            cluster.trustee_password = None
    except Exception:
        # Exceptions are already logged by keystone().delete_trustee
        pass
