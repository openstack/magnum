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

import itertools

from magnum.common.policies import base
from magnum.common.policies import certificate
from magnum.common.policies import cluster
from magnum.common.policies import cluster_template
from magnum.common.policies import federation
from magnum.common.policies import magnum_service
from magnum.common.policies import nodegroup
from magnum.common.policies import quota
from magnum.common.policies import stats


def list_rules():
    return itertools.chain(
        base.list_rules(),
        certificate.list_rules(),
        cluster.list_rules(),
        cluster_template.list_rules(),
        federation.list_rules(),
        magnum_service.list_rules(),
        quota.list_rules(),
        stats.list_rules(),
        nodegroup.list_rules()
    )
