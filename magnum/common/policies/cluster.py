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

from magnum.common.policies import base

CLUSTER = 'cluster:%s'

rules = [
    policy.DocumentedRuleDefault(
        name=CLUSTER % 'create',
        check_str=base.RULE_ADMIN_OR_PROJECT_MEMBER_DENY_CLUSTER_USER,
        scope_types=["project"],
        description='Create a new cluster.',
        operations=[
            {
                'path': '/v1/clusters',
                'method': 'POST'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name=CLUSTER % 'delete',
        check_str=base.RULE_ADMIN_OR_PROJECT_MEMBER_DENY_CLUSTER_USER,
        scope_types=["project"],
        description='Delete a cluster.',
        operations=[
            {
                'path': '/v1/clusters/{cluster_ident}',
                'method': 'DELETE'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name=CLUSTER % 'delete_all_projects',
        check_str=base.RULE_ADMIN_API,
        description='Delete a cluster from any project.',
        operations=[
            {
                'path': '/v1/clusters/{cluster_ident}',
                'method': 'DELETE'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name=CLUSTER % 'detail',
        check_str=base.RULE_ADMIN_OR_PROJECT_READER_DENY_CLUSTER_USER,
        scope_types=["project"],
        description='Retrieve a list of clusters with detail.',
        operations=[
            {
                'path': '/v1/clusters',
                'method': 'GET'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name=CLUSTER % 'detail_all_projects',
        check_str=base.RULE_ADMIN_API,
        description='Retrieve a list of clusters with detail across projects.',
        operations=[
            {
                'path': '/v1/clusters',
                'method': 'GET'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name=CLUSTER % 'get',
        check_str=base.RULE_ADMIN_OR_PROJECT_READER_DENY_CLUSTER_USER,
        scope_types=["project"],
        description='Retrieve information about the given cluster.',
        operations=[
            {
                'path': '/v1/clusters/{cluster_ident}',
                'method': 'GET'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name=CLUSTER % 'get_one_all_projects',
        check_str=base.RULE_ADMIN_API,
        description=('Retrieve information about the given cluster across '
                     'projects.'),
        operations=[
            {
                'path': '/v1/clusters/{cluster_ident}',
                'method': 'GET'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name=CLUSTER % 'get_all',
        check_str=base.RULE_ADMIN_OR_PROJECT_READER_DENY_CLUSTER_USER,
        scope_types=["project"],
        description='Retrieve a list of clusters.',
        operations=[
            {
                'path': '/v1/clusters/',
                'method': 'GET'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name=CLUSTER % 'get_all_all_projects',
        check_str=base.RULE_ADMIN_API,
        description='Retrieve a list of all clusters across projects.',
        operations=[
            {
                'path': '/v1/clusters/',
                'method': 'GET'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name=CLUSTER % 'update',
        check_str=base.RULE_ADMIN_OR_PROJECT_MEMBER_DENY_CLUSTER_USER,
        scope_types=["project"],
        description='Update an existing cluster.',
        operations=[
            {
                'path': '/v1/clusters/{cluster_ident}',
                'method': 'PATCH'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name=CLUSTER % 'update_health_status',
        check_str=base.RULE_ADMIN_OR_PROJECT_MEMBER_USER_OR_CLUSTER_USER,
        scope_types=["project"],
        description='Update the health status of an existing cluster.',
        operations=[
            {
                'path': '/v1/clusters/{cluster_ident}',
                'method': 'PATCH'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name=CLUSTER % 'update_all_projects',
        check_str=base.RULE_ADMIN_API,
        description='Update an existing cluster.',
        operations=[
            {
                'path': '/v1/clusters/{cluster_ident}',
                'method': 'PATCH'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name=CLUSTER % 'resize',
        check_str=base.RULE_ADMIN_OR_PROJECT_MEMBER_DENY_CLUSTER_USER,
        scope_types=["project"],
        description='Resize an existing cluster.',
        operations=[
            {
                'path': '/v1/clusters/{cluster_ident}/actions/resize',
                'method': 'POST'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name=CLUSTER % 'upgrade',
        check_str=base.RULE_ADMIN_OR_PROJECT_MEMBER_DENY_CLUSTER_USER,
        scope_types=["project"],
        description='Upgrade an existing cluster.',
        operations=[
            {
                'path': '/v1/clusters/{cluster_ident}/actions/upgrade',
                'method': 'POST'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name=CLUSTER % 'upgrade_all_projects',
        check_str=base.RULE_ADMIN_API,
        description='Upgrade an existing cluster across all projects.',
        operations=[
            {
                'path': '/v1/clusters/{cluster_ident}/actions/upgrade',
                'method': 'POST'
            }
        ]
    )

]


def list_rules():
    return rules
