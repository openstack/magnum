# Copyright (c) 2018 European Organization for Nuclear Research.
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


NODEGROUP = 'nodegroup:%s'


rules = [
    policy.DocumentedRuleDefault(
        name=NODEGROUP % 'get',
        check_str=base.RULE_ADMIN_OR_OWNER,
        description='Retrieve information about the given nodegroup.',
        operations=[
            {
                'path': '/v1/clusters/{cluster_id}/nodegroup/{nodegroup}',
                'method': 'GET'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name=NODEGROUP % 'get_all',
        check_str=base.RULE_ADMIN_OR_OWNER,
        description='Retrieve a list of nodegroups that belong to a cluster.',
        operations=[
            {
                'path': '/v1/clusters/{cluster_id}/nodegroups/',
                'method': 'GET'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name=NODEGROUP % 'get_all_all_projects',
        check_str=base.RULE_ADMIN_API,
        description='Retrieve a list of nodegroups across projects.',
        operations=[
            {
                'path': '/v1/clusters/{cluster_id}/nodegroups/',
                'method': 'GET'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name=NODEGROUP % 'get_one_all_projects',
        check_str=base.RULE_ADMIN_API,
        description='Retrieve infornation for a given nodegroup.',
        operations=[
            {
                'path': '/v1/clusters/{cluster_id}/nodegroups/{nodegroup}',
                'method': 'GET'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name=NODEGROUP % 'create',
        check_str=base.RULE_ADMIN_OR_OWNER,
        description='Create a new nodegroup.',
        operations=[
            {
                'path': '/v1/clusters/{cluster_id}/nodegroups/',
                'method': 'POST'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name=NODEGROUP % 'delete',
        check_str=base.RULE_ADMIN_OR_OWNER,
        description='Delete a nodegroup.',
        operations=[
            {
                'path': '/v1/clusters/{cluster_id}/nodegroups/{nodegroup}',
                'method': 'DELETE'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name=NODEGROUP % 'update',
        check_str=base.RULE_ADMIN_OR_OWNER,
        description='Update an existing nodegroup.',
        operations=[
            {
                'path': '/v1/clusters/{cluster_id}/nodegroups/{nodegroup}',
                'method': 'PATCH'
            }
        ]
    ),
]


def list_rules():
    return rules
