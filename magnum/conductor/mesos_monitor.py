#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

from oslo_serialization import jsonutils

from magnum.common import urlfetch
from magnum.conductor import monitors


class MesosMonitor(monitors.MonitorBase):

    def __init__(self, context, cluster):
        super(MesosMonitor, self).__init__(context, cluster)
        self.data = {}

    @property
    def metrics_spec(self):
        return {
            'memory_util': {
                'unit': '%',
                'func': 'compute_memory_util',
            },
            'cpu_util': {
                'unit': '%',
                'func': 'compute_cpu_util',
            },
        }

    def _build_url(self, url, protocol='http', port='80', path='/'):
        return protocol + '://' + url + ':' + port + path

    def _is_leader(self, state):
        return state['leader'] == state['pid']

    def pull_data(self):
        self.data['mem_total'] = 0
        self.data['mem_used'] = 0
        self.data['cpu_total'] = 0
        self.data['cpu_used'] = 0
        for master_addr in self.cluster.master_addresses:
            mesos_master_url = self._build_url(master_addr, port='5050',
                                               path='/state')
            master = jsonutils.loads(urlfetch.get(mesos_master_url))
            if self._is_leader(master):
                for slave in master['slaves']:
                    self.data['mem_total'] += slave['resources']['mem']
                    self.data['mem_used'] += slave['used_resources']['mem']
                    self.data['cpu_total'] += slave['resources']['cpus']
                    self.data['cpu_used'] += slave['used_resources']['cpus']
                break

    def compute_memory_util(self):
        if self.data['mem_total'] == 0 or self.data['mem_used'] == 0:
            return 0
        else:
            return self.data['mem_used'] * 100 / self.data['mem_total']

    def compute_cpu_util(self):
        if self.data['cpu_total'] == 0 or self.data['cpu_used'] == 0:
            return 0
        else:
            return self.data['cpu_used'] * 100 / self.data['cpu_total']
