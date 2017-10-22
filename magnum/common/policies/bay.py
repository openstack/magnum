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

BAY = 'bay:%s'

rules = [
    policy.DocumentedRuleDefault(
        name=BAY % 'create',
        check_str=base.RULE_DENY_CLUSTER_USER,
        description='Create a new bay.',
        operations=[
            {
                'path': '/v1/bays',
                'method': 'POST'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name=BAY % 'delete',
        check_str=base.RULE_DENY_CLUSTER_USER,
        description='Delete a bay.',
        operations=[
            {
                'path': '/v1/bays/{bay_ident}',
                'method': 'DELETE'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name=BAY % 'detail',
        check_str=base.RULE_DENY_CLUSTER_USER,
        description='Retrieve a list of bays with detail.',
        operations=[
            {
                'path': '/v1/bays',
                'method': 'GET'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name=BAY % 'get',
        check_str=base.RULE_DENY_CLUSTER_USER,
        description='Retrieve information about the given bay.',
        operations=[
            {
                'path': '/v1/bays/{bay_ident}',
                'method': 'GET'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name=BAY % 'get_all',
        check_str=base.RULE_DENY_CLUSTER_USER,
        description='Retrieve a list of bays.',
        operations=[
            {
                'path': '/v1/bays/',
                'method': 'GET'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name=BAY % 'update',
        check_str=base.RULE_DENY_CLUSTER_USER,
        description='Update an existing bay.',
        operations=[
            {
                'path': '/v1/bays/{bay_ident}',
                'method': 'PATCH'
            }
        ]
    )
]


def list_rules():
    return rules
