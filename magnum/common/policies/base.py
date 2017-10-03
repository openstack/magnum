# All Rights Reserved.
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
from oslo_policy import policy

ROLE_ADMIN = 'rule:context_is_admin'
RULE_ADMIN_OR_OWNER = 'rule:admin_or_owner'
RULE_ADMIN_API = 'rule:admin_api'
RULE_ADMIN_OR_USER = 'rule:admin_or_user'
RULE_CLUSTER_USER = 'rule:cluster_user'
RULE_DENY_CLUSTER_USER = 'rule:deny_cluster_user'

rules = [
    policy.RuleDefault(
        name='context_is_admin',
        check_str='role:admin'
    ),
    policy.RuleDefault(
        name='admin_or_owner',
        check_str='is_admin:True or project_id:%(project_id)s'
    ),
    policy.RuleDefault(
        name='admin_api',
        check_str='rule:context_is_admin'
    ),
    policy.RuleDefault(
        name='admin_or_user',
        check_str='is_admin:True or user_id:%(user_id)s'
    ),
    policy.RuleDefault(
        name='cluster_user',
        check_str='user_id:%(trustee_user_id)s'
    ),
    policy.RuleDefault(
        name='deny_cluster_user',
        check_str='not domain_id:%(trustee_domain_id)s'
    )
]


def list_rules():
    return rules
