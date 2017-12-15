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

QUOTA = 'quota:%s'

rules = [
    policy.DocumentedRuleDefault(
        name=QUOTA % 'create',
        check_str=base.RULE_ADMIN_API,
        description='Create quota.',
        operations=[
            {
                'path': '/v1/quotas',
                'method': 'POST'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name=QUOTA % 'delete',
        check_str=base.RULE_ADMIN_API,
        description='Delete quota for a given project_id and resource.',
        operations=[
            {
                'path': '/v1/quotas/{project_id}/{resource}',
                'method': 'DELETE'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name=QUOTA % 'get',
        check_str=base.RULE_ADMIN_OR_OWNER,
        description='Retrieve Quota information for the given project_id.',
        operations=[
            {
                'path': '/v1/quotas/{project_id}/{resource}',
                'method': 'GET'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name=QUOTA % 'get_all',
        check_str=base.RULE_ADMIN_API,
        description='Retrieve a list of quotas.',
        operations=[
            {
                'path': '/v1/quotas',
                'method': 'GET'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name=QUOTA % 'update',
        check_str=base.RULE_ADMIN_API,
        description='Update quota for a given project_id.',
        operations=[
            {
                'path': '/v1/quotas/{project_id}/{resource}',
                'method': 'PATCH'
            }
        ]
    )
]


def list_rules():
    return rules
