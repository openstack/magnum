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

from magnum.objects import bay
from magnum.objects import baylock
from magnum.objects import baymodel
from magnum.objects import container
from magnum.objects import node
from magnum.objects import pod
from magnum.objects import replicationcontroller as rc
from magnum.objects import service
from magnum.objects import x509keypair


Container = container.Container
Bay = bay.Bay
BayLock = baylock.BayLock
BayModel = baymodel.BayModel
Node = node.Node
Pod = pod.Pod
ReplicationController = rc.ReplicationController
Service = service.Service
X509KeyPair = x509keypair.X509KeyPair

__all__ = (Bay,
           BayLock,
           BayModel,
           Container,
           Node,
           Pod,
           ReplicationController,
           Service,
           X509KeyPair)
