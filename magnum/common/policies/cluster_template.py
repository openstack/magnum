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

CLUSTER_TEMPLATE = 'clustertemplate:%s'

rules = [
    policy.DocumentedRuleDefault(
        name=CLUSTER_TEMPLATE % 'create',
        check_str=base.RULE_ADMIN_OR_PROJECT_MEMBER_DENY_CLUSTER_USER,
        scope_types=["project"],
        description='Create a new cluster template.',
        operations=[
            {
                'path': '/v1/clustertemplates',
                'method': 'POST'
            }
        ],
    ),
    policy.DocumentedRuleDefault(
        name=CLUSTER_TEMPLATE % 'delete',
        check_str=base.RULE_ADMIN_OR_PROJECT_MEMBER,
        scope_types=["project"],
        description='Delete a cluster template.',
        operations=[
            {
                'path': '/v1/clustertemplate/{clustertemplate_ident}',
                'method': 'DELETE'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name=CLUSTER_TEMPLATE % 'delete_all_projects',
        check_str=base.RULE_ADMIN_API,
        description='Delete a cluster template from any project.',
        operations=[
            {
                'path': '/v1/clustertemplate/{clustertemplate_ident}',
                'method': 'DELETE'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name=CLUSTER_TEMPLATE % 'detail_all_projects',
        check_str=base.RULE_ADMIN_API,
        description=('Retrieve a list of cluster templates with detail across '
                     'projects.'),
        operations=[
            {
                'path': '/v1/clustertemplates',
                'method': 'GET'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name=CLUSTER_TEMPLATE % 'detail',
        check_str=base.RULE_ADMIN_OR_PROJECT_READER_DENY_CLUSTER_USER,
        scope_types=["project"],
        description='Retrieve a list of cluster templates with detail.',
        operations=[
            {
                'path': '/v1/clustertemplates',
                'method': 'GET'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name=CLUSTER_TEMPLATE % 'get',
        check_str=base.RULE_ADMIN_OR_PROJECT_READER_DENY_CLUSTER_USER,
        scope_types=["project"],
        description='Retrieve information about the given cluster template.',
        operations=[
            {
                'path': '/v1/clustertemplate/{clustertemplate_ident}',
                'method': 'GET'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name=CLUSTER_TEMPLATE % 'get_one_all_projects',
        check_str=base.RULE_ADMIN_API,
        description=('Retrieve information about the given cluster template '
                     'across project.'),
        operations=[
            {
                'path': '/v1/clustertemplate/{clustertemplate_ident}',
                'method': 'GET'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name=CLUSTER_TEMPLATE % 'get_all',
        check_str=base.RULE_ADMIN_OR_PROJECT_READER_DENY_CLUSTER_USER,
        scope_types=["project"],
        description='Retrieve a list of cluster templates.',
        operations=[
            {
                'path': '/v1/clustertemplates',
                'method': 'GET'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name=CLUSTER_TEMPLATE % 'get_all_all_projects',
        check_str=base.RULE_ADMIN_API,
        description='Retrieve a list of cluster templates across projects.',
        operations=[
            {
                'path': '/v1/clustertemplates',
                'method': 'GET'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name=CLUSTER_TEMPLATE % 'update',
        check_str=base.RULE_ADMIN_OR_PROJECT_MEMBER,
        scope_types=["project"],
        description='Update an existing cluster template.',
        operations=[
            {
                'path': '/v1/clustertemplate/{clustertemplate_ident}',
                'method': 'PATCH'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name=CLUSTER_TEMPLATE % 'update_all_projects',
        check_str=base.RULE_ADMIN_API,
        description='Update an existing cluster template.',
        operations=[
            {
                'path': '/v1/clustertemplate/{clustertemplate_ident}',
                'method': 'PATCH'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name=CLUSTER_TEMPLATE % 'publish',
        check_str=base.RULE_ADMIN_API,
        description='Publish an existing cluster template.',
        operations=[
            {
                'path': '/v1/clustertemplates',
                'method': 'POST'
            },
            {
                'path': '/v1/clustertemplates',
                'method': 'PATCH'
            }
        ]
    )
]


def list_rules():
    return rules
