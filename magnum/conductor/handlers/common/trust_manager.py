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

from oslo_config import cfg
from oslo_log import log as logging

from magnum.common import utils

CONF = cfg.CONF
CONF.import_opt('trustee_domain_id', 'magnum.common.keystone',
                group='trust')

LOG = logging.getLogger(__name__)


def create_trustee_and_trust(osc, bay):
    password = utils.generate_password(length=18)
    trustee = osc.keystone().create_trustee(
        bay.uuid,
        password,
        CONF.trust.trustee_domain_id)
    bay.trustee_username = trustee.name
    bay.trustee_user_id = trustee.id
    bay.trustee_password = password
    trust = osc.keystone().create_trust(trustee.id)
    bay.trust_id = trust.id


def delete_trustee_and_trust(osc, bay):
    try:
        # The bay which is upgraded from Liberty doesn't have trust_id
        if bay.trust_id:
            osc.keystone().delete_trust(bay.trust_id)
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
