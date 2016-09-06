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
from oslo_utils import importutils
import six

from magnum.objects import fields


LOG = log.getLogger(__name__)

CONF = cfg.CONF
CONF.import_opt('docker_remote_api_version',
                'magnum.common.docker_utils',
                group='docker')
CONF.import_opt('default_timeout',
                'magnum.common.docker_utils',
                group='docker')

COE_CLASS_PATH = {
    fields.BayType.SWARM: 'magnum.conductor.swarm_monitor.SwarmMonitor',
    fields.BayType.KUBERNETES: 'magnum.conductor.k8s_monitor.K8sMonitor',
    fields.BayType.MESOS: 'magnum.conductor.mesos_monitor.MesosMonitor'
}


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
        """Pull data for monitoring."""

    def get_metric_names(self):
        return self.metrics_spec.keys()

    def get_metric_unit(self, metric_name):
        return self.metrics_spec[metric_name]['unit']

    def compute_metric_value(self, metric_name):
        func_name = self.metrics_spec[metric_name]['func']
        func = getattr(self, func_name)
        return func()


def create_monitor(context, bay):
    if bay.cluster_template.coe in COE_CLASS_PATH:
        coe_cls = importutils.import_class(
            COE_CLASS_PATH[bay.cluster_template.coe])
        return coe_cls(context, bay)

    LOG.debug("Cannot create monitor with bay type '%s'",
              bay.cluster_template.coe)
    return None
