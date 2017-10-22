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

BAYMODEL = 'baymodel:%s'

rules = [
    policy.DocumentedRuleDefault(
        name=BAYMODEL % 'create',
        check_str=base.RULE_DENY_CLUSTER_USER,
        description='Create a new baymodel.',
        operations=[
            {
                'path': '/v1/baymodels',
                'method': 'POST'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name=BAYMODEL % 'delete',
        check_str=base.RULE_DENY_CLUSTER_USER,
        description='Delete a baymodel.',
        operations=[
            {
                'path': '/v1/baymodels/{baymodel_ident}',
                'method': 'DELETE'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name=BAYMODEL % 'detail',
        check_str=base.RULE_DENY_CLUSTER_USER,
        description='Retrieve a list of baymodel with detail.',
        operations=[
            {
                'path': '/v1/baymodels',
                'method': 'GET'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name=BAYMODEL % 'get',
        check_str=base.RULE_DENY_CLUSTER_USER,
        description='Retrieve information about the given baymodel.',
        operations=[
            {
                'path': '/v1/baymodels/{baymodel_ident}',
                'method': 'GET'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name=BAYMODEL % 'get_all',
        check_str=base.RULE_DENY_CLUSTER_USER,
        description='Retrieve a list of baymodel.',
        operations=[
            {
                'path': '/v1/baymodels',
                'method': 'GET'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name=BAYMODEL % 'update',
        check_str=base.RULE_DENY_CLUSTER_USER,
        description='Update an existing baymodel.',
        operations=[
            {
                'path': '/v1/baymodels/{baymodel_ident}',
                'method': 'PATCH'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name=BAYMODEL % 'publish',
        check_str=base.RULE_ADMIN_API,
        description='Publish an existing baymodel.',
        operations=[
            {
                'path': '/v1/baymodels',
                'method': 'POST'
            },
            {
                'path': '/v1/baymodels',
                'method': 'PATCH'
            }
        ]
    )
]


def list_rules():
    return rules
