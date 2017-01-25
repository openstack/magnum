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

from oslo_log import log
import six

from magnum.common import profiler
import magnum.conf
from magnum.drivers.common.driver import Driver


LOG = log.getLogger(__name__)

CONF = magnum.conf.CONF


@profiler.trace_cls("rpc")
@six.add_metaclass(abc.ABCMeta)
class MonitorBase(object):

    def __init__(self, context, cluster):
        self.context = context
        self.cluster = cluster

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


def create_monitor(context, cluster):
    cluster_driver = Driver.get_driver_for_cluster(context, cluster)
    monitor = cluster_driver.get_monitor(context, cluster)
    if monitor:
        return monitor

    LOG.debug("Cannot create monitor with cluster type '%s'",
              cluster.cluster_template.coe)
    return None
