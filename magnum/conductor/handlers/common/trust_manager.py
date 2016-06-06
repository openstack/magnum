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
from magnum.i18n import _LE

LOG = logging.getLogger(__name__)


def create_trustee_and_trust(osc, bay):
    try:
        password = utils.generate_password(length=18)
        trustee = osc.keystone().create_trustee(
            bay.uuid,
            password,
        )
        bay.trustee_username = trustee.name
        bay.trustee_user_id = trustee.id
        bay.trustee_password = password
        trust = osc.keystone().create_trust(trustee.id)
        bay.trust_id = trust.id
    except Exception:
        LOG.exception(_LE('Failed to create trustee and trust for Bay: %s'),
                      bay.uuid)
        raise exception.TrusteeOrTrustToBayFailed(bay_uuid=bay.uuid)


def delete_trustee_and_trust(osc, context, bay):
    try:
        # The bay which is upgraded from Liberty doesn't have trust_id
        if bay.trust_id:
            osc.keystone().delete_trust(context, bay)
    except Exception:
        # Exceptions are already logged by keystone().delete_trust
        pass
    try:
        # The bay which is upgraded from Liberty doesn't have trustee_user_id
        if bay.trustee_user_id:
            osc.keystone().delete_trustee(bay.trustee_user_id)
    except Exception:
        # Exceptions are already logged by keystone().delete_trustee
        pass
