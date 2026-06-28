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

from magnum.common import clients
from magnum.common import context as mag_ctx
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


def _trust_exists(trust_id):
    """Return True if the trust still exists in Keystone.

    Validated with an admin context so a trust owned by a different trustor
    than the current caller is not mistaken for broken (which would cause an
    unnecessary trustor swap whenever a non-trustor operator runs an upgrade).
    """
    try:
        adm = clients.OpenStackClients(mag_ctx.make_admin_context())
        adm.keystone().client.trusts.get(trust_id)
        return True
    except Exception as e:
        LOG.warning('Cluster trust %s is missing or invalid: %s', trust_id, e)
        return False


def ensure_trust(osc, context, cluster):
    """Validate the cluster's Keystone trust and recreate it if broken.

    Keystone destroys a trust when its trustor user is deleted -- e.g. an
    OIDC/federated shadow user that was disabled or removed. Re-enabling the
    user does NOT restore the trust, so the cluster keeps a dangling
    ``trust_id`` and every trust-auth consumer (the conductor, plus the
    in-cluster OCCM / Cinder-CSI / Manila-CSI / magnum-auto-healer pods) gets
    ``403 Forbidden`` on ``POST /v3/auth/tokens``.

    Detect that and recreate the trust delegating to the cluster's existing
    trustee, with the current request user (the operator running the upgrade)
    as the new trustor. The caller must hold the roles the cluster needs;
    ``create_trust`` delegates ``context.roles`` (or ``CONF.trust.roles``).

    The new ``trust_id`` is persisted before the Heat update so it propagates
    through heat-params into the node cloud.conf and on to the cloud
    controllers.

    :param osc: OpenStackClients built from the request ``context``; its user
        becomes the new trustor on recreate
    :param context: request context of the operator triggering the operation
    :param cluster: the cluster whose trust to ensure
    :returns: True if the trust was recreated, False if it was already valid
        or the cluster predates trusts
    """
    # Liberty-era clusters never had a trust; nothing to ensure.
    if not cluster.trustee_user_id:
        return False

    if cluster.trust_id and _trust_exists(cluster.trust_id):
        return False

    old_trust_id = cluster.trust_id
    try:
        trust = osc.keystone().create_trust(cluster.trustee_user_id)
    except Exception:
        LOG.exception(
            'Failed to recreate trust for cluster %s (trustee %s, trustor %s)',
            cluster.uuid, cluster.trustee_user_id, context.user_id)
        raise exception.TrusteeOrTrustToClusterFailed(
            cluster_uuid=cluster.uuid)

    cluster.trust_id = trust.id
    cluster.save()
    LOG.warning(
        'Recreated broken trust for cluster %s: trustor is now %s, '
        'trust_id %s -> %s',
        cluster.uuid, context.user_id, old_trust_id, trust.id)
    return True


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
