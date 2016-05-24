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
from magnum.objects import baymodel
from magnum.objects import certificate
from magnum.objects import container
from magnum.objects import magnum_service
from magnum.objects import replicationcontroller as rc
from magnum.objects import x509keypair


Container = container.Container
Bay = bay.Bay
BayModel = baymodel.BayModel
MagnumService = magnum_service.MagnumService
ReplicationController = rc.ReplicationController
X509KeyPair = x509keypair.X509KeyPair
Certificate = certificate.Certificate
__all__ = (Bay,
           BayModel,
           Container,
           MagnumService,
           ReplicationController,
           X509KeyPair,
           Certificate)
