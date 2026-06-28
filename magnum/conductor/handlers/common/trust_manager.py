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

from keystoneauth1 import exceptions as ka_exception
from oslo_log import log as logging

from magnum.common import clients
from magnum.common import context as mag_ctx
from magnum.common import exception
from magnum.common import utils
import magnum.conf

CONF = magnum.conf.CONF
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


def _recreate_trust(osc, context, cluster):
    """Recreate a missing trust delegating to the cluster's existing trustee.

    Used only when the trust is genuinely gone (e.g. the trustor user was
    *deleted*, not merely disabled). The current request user becomes the new
    trustor, so the operator running the upgrade must hold the roles the
    cluster needs (``create_trust`` delegates ``context.roles`` or
    ``CONF.trust.roles``). The new ``trust_id`` is persisted before the Heat
    update so it propagates through heat-params into the node cloud.conf.
    """
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
        'Recreated missing trust for cluster %s: trustor is now %s, '
        'trust_id %s -> %s',
        cluster.uuid, context.user_id, old_trust_id, trust.id)
    return True


def _heal_trustor_roles(cluster, trustor_user_id, project_id, roles):
    """Re-grant a trust's delegated roles to its trustor (idempotent).

    The common real-world breakage: the cluster creator (the trustor) was
    disabled and lost their project role assignments, then re-enabled. The
    trust still exists but cannot be redeemed, because Keystone requires the
    trustor to currently hold every delegated role -- so each trust-scoped
    token (conductor, Heat, OCCM, Cinder/Manila CSI, magnum-auto-healer) fails
    with 401/403. Re-granting exactly the delegated roles restores redemption.

    ``roles`` is a list of ``(role_id, role_name)`` tuples.
    """
    admin = clients.OpenStackClients(mag_ctx.make_admin_context()).keystone()
    granted = []
    for role_id, role_name in roles:
        if not role_id:
            continue
        try:
            admin.grant_role(role_id, trustor_user_id, project_id)
            granted.append(role_name or role_id)
        except Exception as e:
            LOG.warning(
                'Cluster %s: could not grant role %s to trustor %s on '
                'project %s: %s',
                cluster.uuid, role_name or role_id, trustor_user_id,
                project_id, e)
    if granted:
        LOG.warning(
            'Cluster %s: healed trust by granting trustor %s the delegated '
            'role(s) %s on project %s',
            cluster.uuid, trustor_user_id, granted, project_id)


def ensure_trust(osc, context, cluster):
    """Ensure the cluster's Keystone trust is usable before an upgrade.

    Two distinct failures are handled:

    1. **Trust role-stripped (common).** The trust still exists but its
       trustor (the cluster creator) no longer holds the delegated roles --
       e.g. the creator was disabled, which removes their project role
       assignments, then re-enabled. The trust cannot be redeemed, so the
       conductor's Heat update and the in-cluster cloud controllers all get
       401/403. Fixed by re-granting the trust's delegated roles to the
       trustor (gated by ``CONF.trust.heal_trustor_roles``).

    2. **Trust missing (rare).** The trust is genuinely gone (trustor user
       deleted). Recreated with the upgrade caller as the new trustor.

    The trust is read **as the trustee** -- the upgrade caller is not a party
    to the trust, and a project-scoped admin token cannot read another user's
    trust (Keystone policy needs system scope), so only the trustee read is
    reliable. An unscoped trustee token is used because a trust-scoped token is
    exactly what is unobtainable when the trustor lost its roles.

    :param osc: OpenStackClients built from the request ``context``
    :param context: request context of the operator triggering the operation
    :param cluster: the cluster whose trust to ensure
    :returns: True if the trust was recreated, False otherwise
    """
    # Liberty-era clusters never had a trust; nothing to ensure.
    if not cluster.trustee_user_id:
        return False

    # No trust recorded at all -> create one.
    if not cluster.trust_id:
        return _recreate_trust(osc, context, cluster)

    try:
        trust = osc.keystone().get_trust_as_trustee(
            cluster.trustee_user_id, cluster.trustee_password,
            cluster.trust_id)
    except ka_exception.NotFound:
        LOG.warning('Cluster %s trust %s no longer exists; recreating',
                    cluster.uuid, cluster.trust_id)
        return _recreate_trust(osc, context, cluster)
    except Exception as e:
        # Could not verify the trust (e.g. trustee auth failed). Leave it
        # untouched rather than risk a needless recreate or wrong re-grant.
        LOG.warning(
            'Cluster %s: could not read trust %s as trustee (%s); skipping '
            'trust heal', cluster.uuid, cluster.trust_id, e)
        return False

    # Trust is alive -- re-grant its delegated roles to the trustor so it can
    # be redeemed even if the trustor was role-stripped.
    if CONF.trust.heal_trustor_roles:
        roles = [(r.get('id'), r.get('name')) for r in (trust.roles or [])]
        _heal_trustor_roles(cluster, trust.trustor_user_id,
                            getattr(trust, 'project_id', cluster.project_id),
                            roles)
    return False


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
