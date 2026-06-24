# Copyright 2016 Rackspace Inc. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import os
import six.moves.urllib.parse as urlparse

from magnum.common import utils
import magnum.conf
from magnum.drivers.heat import k8s_ubuntu_template_def as kftd

CONF = magnum.conf.CONF


class UBUNTUK8sTemplateDefinition(kftd.K8sUbuntuTemplateDefinition):
    """Kubernetes template for a Ubuntu VM."""

    @property
    def driver_module_path(self):
        return __name__[:__name__.rindex('.')]

    @property
    def template_path(self):
        return os.path.join(os.path.dirname(os.path.realpath(__file__)),
                            'templates/kubecluster.yaml')

    def get_discovery_url(self, cluster):
        # The etcd v2 discovery protocol (discovery.etcd.io) has been removed:
        # the node reconciler bootstraps etcd via the etcd load balancer or a
        # static initial cluster. The base class would otherwise fetch a
        # discovery token at create time, which fails on a Magnum control plane
        # without internet egress. Short-circuit it; the 'discovery_url' stack
        # parameter has been dropped from the templates and get_params() strips
        # any residual value.
        return ''

    def get_params(self, context, cluster_template, cluster, **kwargs):
        extra_params = super(UBUNTUK8sTemplateDefinition,
                             self).get_params(context,
                                              cluster_template,
                                              cluster,
                                              **kwargs)
        # discovery_url is no longer a template parameter (etcd v2 discovery
        # removed) — drop it so Heat does not reject an undefined parameter.
        extra_params.pop('discovery_url', None)
        extra_params['openstack_ca'] = urlparse.quote(
            utils.get_openstack_ca())
        return extra_params
