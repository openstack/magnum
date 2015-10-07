# Copyright 2015 Huawei Technologies Co.,LTD.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import abc

from oslo_config import cfg
from oslo_log import log
import six

from magnum.common import docker_utils
from magnum.i18n import _LW
from magnum import objects
from magnum.objects.fields import BayType as bay_type


LOG = log.getLogger(__name__)

CONF = cfg.CONF
CONF.import_opt('docker_remote_api_version',
                'magnum.conductor.handlers.docker_conductor',
                group='docker')
CONF.import_opt('default_timeout',
                'magnum.conductor.handlers.docker_conductor',
                group='docker')


@six.add_metaclass(abc.ABCMeta)
class MonitorBase(object):

    def __init__(self, context, bay):
        self.context = context
        self.bay = bay

    @abc.abstractproperty
    def metrics_spec(self):
        """Metric specification."""

    @abc.abstractmethod
    def pull_data(self):
        """Pull data from bay."""

    def get_metric_names(self):
        return self.metrics_spec.keys()

    def get_metric_unit(self, metric_name):
        return self.metrics_spec[metric_name]['unit']

    def compute_metric_value(self, metric_name):
        func_name = self.metrics_spec[metric_name]['func']
        func = getattr(self, func_name)
        return func()


class SwarmMonitor(MonitorBase):

    def __init__(self, context, bay):
        super(SwarmMonitor, self).__init__(context, bay)
        self.data = {}
        self.data['nodes'] = []
        self.data['containers'] = []

    @property
    def metrics_spec(self):
        return {
            'memory_util': {
                'unit': '%',
                'func': 'compute_memory_util',
            },
        }

    def pull_data(self):
        with docker_utils.docker_for_bay(self.context,
                                         self.bay) as docker:
            system_info = docker.info()
            self.data['nodes'] = self._parse_node_info(system_info)

            # pull data from each container
            containers = []
            for container in docker.containers(all=True):
                try:
                    container = docker.inspect_container(container['Id'])
                except Exception as e:
                    LOG.warn(_LW("Ignore error [%(e)s] when inspecting "
                                 "container %(container_id)s."),
                             {'e': e, 'container_id': container['Id']},
                             exc_info=True)
                containers.append(container)
            self.data['containers'] = containers

    def compute_memory_util(self):
        mem_total = 0
        for node in self.data['nodes']:
            mem_total += node['MemTotal']
        mem_reserved = 0
        for container in self.data['containers']:
            mem_reserved += container['Config']['Memory']

        if mem_total == 0:
            return 0
        else:
            return mem_reserved * 100 / mem_total

    def _parse_node_info(self, system_info):
        """Parse system_info to retrieve memory size of each node.

        :param system_info: The output returned by docker.info(). Example:
            {
                u'Debug': False,
                u'NEventsListener': 0,
                u'DriverStatus': [
                    [u'\x08Strategy', u'spread'],
                    [u'\x08Filters', u'...'],
                    [u'\x08Nodes', u'2'],
                    [u'node1', u'10.0.0.4:2375'],
                    [u' \u2514 Containers', u'1'],
                    [u' \u2514 Reserved CPUs', u'0 / 1'],
                    [u' \u2514 Reserved Memory', u'0 B / 2.052 GiB'],
                    [u'node2', u'10.0.0.3:2375'],
                    [u' \u2514 Containers', u'2'],
                    [u' \u2514 Reserved CPUs', u'0 / 1'],
                    [u' \u2514 Reserved Memory', u'0 B / 2.052 GiB']
                ],
                u'Containers': 3
            }
        :return: Memory size of each node. Excample:
            [{'MemTotal': 2203318222.848},
             {'MemTotal': 2203318222.848}]
        """
        nodes = []
        for info in system_info['DriverStatus']:
            key = info[0]
            value = info[1]
            if key == u' \u2514 Reserved Memory':
                memory = value  # Example: '0 B / 2.052 GiB'
                memory = memory.split('/')[1].strip()  # Example: '2.052 GiB'
                memory = memory.split(' ')[0]  # Example: '2.052'
                memory = float(memory) * 1024 * 1024 * 1024
                nodes.append({'MemTotal': memory})
        return nodes


def create_monitor(context, bay):
    baymodel = objects.BayModel.get_by_uuid(context, bay.baymodel_id)
    if baymodel.coe == bay_type.SWARM:
        return SwarmMonitor(context, bay)

    # TODO(hongbin): add support for other bay types
    LOG.debug("Cannot create monitor with bay type '%s'" % baymodel.coe)
    return None
