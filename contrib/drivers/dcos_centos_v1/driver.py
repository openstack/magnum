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

from magnum.drivers.dcos_centos_v1 import monitor
from magnum.drivers.dcos_centos_v1.scale_manager import DcosScaleManager
from magnum.drivers.dcos_centos_v1 import template_def
from magnum.drivers.heat import driver


class Driver(driver.HeatDriver):

    @property
    def provides(self):
        return [
            {'server_type': 'vm',
             'os': 'centos',
             'coe': 'dcos'},
        ]

    def get_template_definition(self):
        return template_def.DcosCentosVMTemplateDefinition()

    def get_monitor(self, context, cluster):
        return monitor.DcosMonitor(context, cluster)

    def get_scale_manager(self, context, osclient, cluster):
        return DcosScaleManager(context, osclient, cluster)
