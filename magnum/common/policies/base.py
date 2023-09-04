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


RULE_ADMIN_OR_OWNER = 'rule:admin_or_owner'
RULE_ADMIN_API = 'rule:context_is_admin'
RULE_ADMIN_OR_USER = 'rule:admin_or_user'
RULE_CLUSTER_USER = 'rule:cluster_user'
RULE_DENY_CLUSTER_USER = 'rule:deny_cluster_user'
RULE_USER = "rule:is_user"
# Generic check string for checking if a user is authorized on a particular
# project, specifically with the member role.
RULE_PROJECT_MEMBER = 'rule:project_member'
# Generic check string for checking if a user is authorized on a particular
# project but with read-only access. For example, this persona would be able to
# list private images owned by a project but cannot make any writeable changes
# to those images.
RULE_PROJECT_READER = 'rule:project_reader'

RULE_USER_OR_CLUSTER_USER = (
    'rule:user_or_cluster_user')
RULE_ADMIN_OR_PROJECT_READER = (
    'rule:admin_or_project_reader')
RULE_ADMIN_OR_PROJECT_MEMBER = (
    'rule:admin_or_project_member')
RULE_ADMIN_OR_PROJECT_MEMBER_USER = (
    'rule:admin_or_project_member_user')
RULE_ADMIN_OR_PROJECT_MEMBER_USER_OR_CLUSTER_USER = (
    'rule:admin_or_project_member_user_or_cluster_user')
RULE_PROJECT_MEMBER_DENY_CLUSTER_USER = (
    'rule:project_member_deny_cluster_user')
RULE_ADMIN_OR_PROJECT_MEMBER_DENY_CLUSTER_USER = (
    'rule:admin_or_project_member_deny_cluster_user')
RULE_PROJECT_READER_DENY_CLUSTER_USER = (
    'rule:project_reader_deny_cluster_user')
RULE_ADMIN_OR_PROJECT_READER_DENY_CLUSTER_USER = (
    'rule:admin_or_project_reader_deny_cluster_user')
RULE_ADMIN_OR_PROJECT_READER_USER = (
    'rule:admin_or_project_reader_user')

# ==========================================================
# Deprecated Since OpenStack 2023.2(Magnum 17.0.0) and should be removed in
# The following cycle.

DEPRECATED_REASON = """
The Magnum API now enforces scoped tokens and default reader and member roles.
"""

DEPRECATED_SINCE = 'OpenStack 2023.2(Magnum 17.0.0)'


DEPRECATED_DENY_CLUSTER_USER = policy.DeprecatedRule(
    name=RULE_DENY_CLUSTER_USER,
    check_str='not domain_id:%(trustee_domain_id)s',
    deprecated_reason=DEPRECATED_REASON,
    deprecated_since=DEPRECATED_SINCE
)

DEPRECATED_RULE_ADMIN_OR_OWNER = policy.DeprecatedRule(
    name=RULE_ADMIN_OR_OWNER,
    check_str='is_admin:True or project_id:%(project_id)s',
    deprecated_reason=DEPRECATED_REASON,
    deprecated_since=DEPRECATED_SINCE
)

# Only used for DEPRECATED_RULE_ADMIN_OR_USER_OR_CLUSTER_USER
RULE_ADMIN_OR_USER_OR_CLUSTER_USER = (
    'rule:admin_or_user_or_cluster_user')

DEPRECATED_RULE_ADMIN_OR_USER_OR_CLUSTER_USER = policy.DeprecatedRule(
    name=RULE_ADMIN_OR_USER_OR_CLUSTER_USER,
    check_str=f"(({RULE_ADMIN_API}) or ({RULE_USER_OR_CLUSTER_USER}))",
    deprecated_reason=DEPRECATED_REASON,
    deprecated_since=DEPRECATED_SINCE
)

DEPRECATED_RULE_ADMIN_OR_USER = policy.DeprecatedRule(
    name=RULE_ADMIN_OR_USER,
    check_str=f"(({RULE_ADMIN_API}) or ({RULE_USER}))",
    deprecated_reason=DEPRECATED_REASON,
    deprecated_since=DEPRECATED_SINCE
)
# ==========================================================

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
        name='admin_or_user',
        check_str='is_admin:True or user_id:%(user_id)s'
    ),
    policy.RuleDefault(
        name='is_user',
        check_str='user_id:%(user_id)s'
    ),
    policy.RuleDefault(
        name='cluster_user',
        check_str='user_id:%(trustee_user_id)s'
    ),
    policy.RuleDefault(
        name='deny_cluster_user',
        check_str='not domain_id:%(trustee_domain_id)s'
    ),
    policy.RuleDefault(
        name='project_member',
        check_str='role:member and project_id:%(project_id)s'
    ),
    policy.RuleDefault(
        name='project_reader',
        check_str='role:reader and project_id:%(project_id)s'
    ),
    policy.RuleDefault(
        name='admin_or_project_reader',
        check_str=f"({RULE_ADMIN_API}) or ({RULE_PROJECT_READER})",
        deprecated_rule=DEPRECATED_RULE_ADMIN_OR_OWNER
    ),
    policy.RuleDefault(
        name='admin_or_project_member',
        check_str=f"({RULE_ADMIN_API}) or ({RULE_PROJECT_MEMBER})",
        deprecated_rule=DEPRECATED_RULE_ADMIN_OR_OWNER
    ),
    policy.RuleDefault(
        name='admin_or_project_member_user',
        check_str=(
            f"({RULE_ADMIN_API}) or (({RULE_PROJECT_MEMBER}) and "
            f"({RULE_USER}))"
        ),
        deprecated_rule=DEPRECATED_RULE_ADMIN_OR_USER
    ),
    policy.RuleDefault(
        name='user_or_cluster_user',
        check_str=(
            f"(({RULE_USER}) or ({RULE_CLUSTER_USER}))"
        )
    ),
    policy.RuleDefault(
        name='admin_or_user_or_cluster_user',
        check_str=(
            f"(({RULE_ADMIN_API}) or ({RULE_USER_OR_CLUSTER_USER}))"
        )
    ),
    policy.RuleDefault(
        name='admin_or_project_member_cluster_user',
        check_str=(
            f"({RULE_ADMIN_API}) or (({RULE_PROJECT_MEMBER}) "
            f"and ({RULE_CLUSTER_USER}))"
        )
    ),
    policy.RuleDefault(
        name='admin_or_project_member_user_or_cluster_user',
        check_str=(
            f"({RULE_ADMIN_API}) or (({RULE_PROJECT_MEMBER}) and "
            f"({RULE_USER_OR_CLUSTER_USER}))"
        ),
        deprecated_rule=DEPRECATED_RULE_ADMIN_OR_USER_OR_CLUSTER_USER
    ),
    policy.RuleDefault(
        name='project_member_deny_cluster_user',
        check_str=(
            f"(({RULE_PROJECT_MEMBER}) and ({RULE_DENY_CLUSTER_USER}))"
        ),
        deprecated_rule=DEPRECATED_DENY_CLUSTER_USER
    ),
    policy.RuleDefault(
        name='admin_or_project_member_deny_cluster_user',
        check_str=(
            f"({RULE_ADMIN_API}) or ({RULE_PROJECT_MEMBER_DENY_CLUSTER_USER})"
        ),
        deprecated_rule=DEPRECATED_DENY_CLUSTER_USER
    ),
    policy.RuleDefault(
        name='project_reader_deny_cluster_user',
        check_str=(
            f"(({RULE_PROJECT_READER}) and ({RULE_DENY_CLUSTER_USER}))"
        ),
        deprecated_rule=DEPRECATED_DENY_CLUSTER_USER
    ),
    policy.RuleDefault(
        name='admin_or_project_reader_deny_cluster_user',
        check_str=(
            f"({RULE_ADMIN_API}) or ({RULE_PROJECT_READER_DENY_CLUSTER_USER})"
        ),
        deprecated_rule=DEPRECATED_DENY_CLUSTER_USER
    ),
    policy.RuleDefault(
        name='admin_or_project_reader_user',
        check_str=(
            f"({RULE_ADMIN_API}) or (({RULE_PROJECT_READER}) and "
            f"({RULE_USER}))"
        ),
        deprecated_rule=DEPRECATED_RULE_ADMIN_OR_USER
    ),
]


def list_rules():
    return rules
