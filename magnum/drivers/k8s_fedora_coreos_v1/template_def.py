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
from magnum.drivers.heat import k8s_fedora_template_def as kftd

CONF = magnum.conf.CONF


class FCOSK8sTemplateDefinition(kftd.K8sFedoraTemplateDefinition):
    """Kubernetes template for a Fedora Atomic VM."""

    @property
    def driver_module_path(self):
        return __name__[:__name__.rindex('.')]

    @property
    def template_path(self):
        return os.path.join(os.path.dirname(os.path.realpath(__file__)),
                            'templates/kubecluster.yaml')

    def get_params(self, context, cluster_template, cluster, **kwargs):
        extra_params = super(FCOSK8sTemplateDefinition,
                             self).get_params(context,
                                              cluster_template,
                                              cluster,
                                              **kwargs)
        extra_params['openstack_ca'] = urlparse.quote(
            utils.get_openstack_ca())
        return extra_params
