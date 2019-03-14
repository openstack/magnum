# Copyright 2016 Fujitsu Ltd.
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

from oslo_config import cfg

from magnum.conf import api
from magnum.conf import barbican
from magnum.conf import certificates
from magnum.conf import cinder
from magnum.conf import cluster
from magnum.conf import cluster_heat
from magnum.conf import cluster_templates
from magnum.conf import conductor
from magnum.conf import database
from magnum.conf import docker
from magnum.conf import docker_registry
from magnum.conf import drivers
from magnum.conf import glance
from magnum.conf import heat
from magnum.conf import keystone
from magnum.conf import kubernetes
from magnum.conf import magnum_client
from magnum.conf import neutron
from magnum.conf import nova
from magnum.conf import octavia
from magnum.conf import paths
from magnum.conf import profiler
from magnum.conf import quota
from magnum.conf import rpc
from magnum.conf import services
from magnum.conf import trust
from magnum.conf import utils
from magnum.conf import x509

CONF = cfg.CONF

api.register_opts(CONF)
barbican.register_opts(CONF)
cluster.register_opts(CONF)
cluster_templates.register_opts(CONF)
cluster_heat.register_opts(CONF)
certificates.register_opts(CONF)
cinder.register_opts(CONF)
conductor.register_opts(CONF)
database.register_opts(CONF)
docker.register_opts(CONF)
docker_registry.register_opts(CONF)
drivers.register_opts(CONF)
glance.register_opts(CONF)
heat.register_opts(CONF)
keystone.register_opts(CONF)
kubernetes.register_opts(CONF)
magnum_client.register_opts(CONF)
neutron.register_opts(CONF)
nova.register_opts(CONF)
octavia.register_opts(CONF)
paths.register_opts(CONF)
quota.register_opts(CONF)
rpc.register_opts(CONF)
services.register_opts(CONF)
trust.register_opts(CONF)
utils.register_opts(CONF)
x509.register_opts(CONF)
profiler.register_opts(CONF)
