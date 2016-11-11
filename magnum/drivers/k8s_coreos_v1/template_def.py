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

import magnum.conf
from magnum.drivers.heat import k8s_template_def
from magnum.drivers.heat import template_def

CONF = magnum.conf.CONF


class CoreOSK8sTemplateDefinition(k8s_template_def.K8sTemplateDefinition):
    """Kubernetes template for CoreOS VM."""

    def __init__(self):
        super(CoreOSK8sTemplateDefinition, self).__init__()
        self.add_output('kube_minions',
                        cluster_attr='node_addresses')
        self.add_output('kube_masters',
                        cluster_attr='master_addresses')

    def get_env_files(self, cluster_template):
        if cluster_template.master_lb_enabled:
            return [template_def.COMMON_ENV_PATH + 'with_master_lb.yaml']
        else:
            return [template_def.COMMON_ENV_PATH + 'no_master_lb.yaml']

    @property
    def driver_module_path(self):
        return __name__[:__name__.rindex('.')]

    @property
    def template_path(self):
        return os.path.join(os.path.dirname(os.path.realpath(__file__)),
                            'templates/kubecluster.yaml')
