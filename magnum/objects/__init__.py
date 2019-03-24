#    Copyright 2013 IBM Corp.
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

from magnum.objects import certificate
from magnum.objects import cluster
from magnum.objects import cluster_template
from magnum.objects import federation
from magnum.objects import magnum_service
from magnum.objects import nodegroup
from magnum.objects import quota
from magnum.objects import stats
from magnum.objects import x509keypair


Cluster = cluster.Cluster
ClusterTemplate = cluster_template.ClusterTemplate
MagnumService = magnum_service.MagnumService
Quota = quota.Quota
X509KeyPair = x509keypair.X509KeyPair
Certificate = certificate.Certificate
Stats = stats.Stats
Federation = federation.Federation
NodeGroup = nodegroup.NodeGroup
__all__ = (Cluster,
           ClusterTemplate,
           MagnumService,
           X509KeyPair,
           Certificate,
           Stats,
           Quota,
           Federation,
           NodeGroup
           )
