# Copyright 2015 Huawei Technologies Co.,LTD.
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

import abc
from oslo_log import log as logging

from magnum.common import exception
from magnum.drivers.common.driver import Driver
from magnum.i18n import _
from magnum import objects


LOG = logging.getLogger(__name__)


def get_scale_manager(context, osclient, cluster):
    cluster_driver = Driver.get_driver_for_cluster(context, cluster)
    manager = cluster_driver.get_scale_manager(context, osclient, cluster)

    # NOTE: Currently only kubernetes cluster scale managers
    # are available.
    return manager


class ScaleManager(object):

    def __init__(self, context, osclient, cluster):
        self.context = context
        self.osclient = osclient
        self.old_cluster = objects.Cluster.get_by_uuid(context, cluster.uuid)
        self.new_cluster = cluster

    def get_removal_nodes(self, hosts_output):
        if not self._is_scale_down():
            return list()

        cluster = self.new_cluster
        stack = self.osclient.heat().stacks.get(cluster.stack_id)
        hosts = hosts_output.get_output_value(stack, cluster)
        if hosts is None:
            raise exception.MagnumException(_(
                "Output key '%(output_key)s' is missing from stack "
                "%(stack_id)s") % {'output_key': hosts_output.heat_output,
                                   'stack_id': stack.id})

        hosts_with_container = self._get_hosts_with_container(self.context,
                                                              cluster)
        hosts_no_container = list(set(hosts) - hosts_with_container)
        LOG.debug('List of hosts that has no container: %s',
                  str(hosts_no_container))

        num_of_removal = self._get_num_of_removal()
        if len(hosts_no_container) < num_of_removal:
            LOG.warning(
                "About to remove %(num_removal)d nodes, which is larger than "
                "the number of empty nodes (%(num_empty)d). %(num_non_empty)d "
                "non-empty nodes will be removed.", {
                    'num_removal': num_of_removal,
                    'num_empty': len(hosts_no_container),
                    'num_non_empty': num_of_removal - len(hosts_no_container)})

        hosts_to_remove = hosts_no_container[0:num_of_removal]
        LOG.info('Require removal of hosts: %s', hosts_to_remove)

        return hosts_to_remove

    def _is_scale_down(self):
        return self.new_cluster.node_count < self.old_cluster.node_count

    def _get_num_of_removal(self):
        return self.old_cluster.node_count - self.new_cluster.node_count

    @abc.abstractmethod
    def _get_hosts_with_container(self, context, cluster):
        """Return the hosts with container running on them."""
        pass
