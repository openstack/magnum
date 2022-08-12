# Copyright 2014 NEC Corporation.  All rights reserved.
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
import six

from oslo_config import cfg
from pkg_resources import iter_entry_points
from stevedore import driver

from magnum.common import exception
from magnum.objects import cluster_template


CONF = cfg.CONF


@six.add_metaclass(abc.ABCMeta)
class Driver(object):

    definitions = None

    @classmethod
    def load_entry_points(cls):
        for entry_point in iter_entry_points('magnum.drivers'):
            if entry_point.name not in CONF.drivers.disabled_drivers:
                yield entry_point, entry_point.load(require=False)

    @classmethod
    def get_drivers(cls):
        """Retrieves cluster drivers from python entry_points.

        Example:

        With the following classes:
        class Driver1(Driver):
            provides = [
                ('server_type1', 'os1', 'coe1')
            ]

        class Driver2(Driver):
            provides = [
                ('server_type2', 'os2', 'coe2')
            ]

        And the following entry_points:

        magnum.drivers =
            driver_name_1 = some.python.path:Driver1
            driver_name_2 = some.python.path:Driver2

        get_drivers will return:
            {
                (server_type1, os1, coe1):
                    {'driver_name_1': Driver1},
                (server_type2, os2, coe2):
                    {'driver_name_2': Driver2}
            }

        :return: dict
        """

        if not cls.definitions:
            cls.definitions = dict()
            for entry_point, def_class in cls.load_entry_points():
                for cluster_type in def_class().provides:
                    cluster_type_tuple = (cluster_type['server_type'],
                                          cluster_type['os'],
                                          cluster_type['coe'])
                    providers = cls.definitions.setdefault(cluster_type_tuple,
                                                           dict())
                    providers['entry_point_name'] = entry_point.name
                    providers['class'] = def_class

        return cls.definitions

    @classmethod
    def get_driver(cls, server_type, os, coe):
        """Get Driver.

        Returns the Driver class for the provided cluster_type.

        With the following classes:
        class Driver1(Driver):
            provides = [
                ('server_type1', 'os1', 'coe1')
            ]

        class Driver2(Driver):
            provides = [
                ('server_type2', 'os2', 'coe2')
            ]

        And the following entry_points:

        magnum.drivers =
            driver_name_1 = some.python.path:Driver1
            driver_name_2 = some.python.path:Driver2

        get_driver('server_type2', 'os2', 'coe2')
        will return: Driver2

        :param server_type: The server_type the cluster definition will build
                            on
        :param os: The operating system the cluster definition will build on
        :param coe: The Container Orchestration Environment the cluster will
                    produce

        :return: class
        """

        definition_map = cls.get_drivers()
        cluster_type = (server_type, os, coe)

        if cluster_type not in definition_map:
            raise exception.ClusterTypeNotSupported(
                server_type=server_type,
                os=os,
                coe=coe)
        driver_info = definition_map[cluster_type]
        # TODO(muralia): once --drivername is supported as an input during
        # cluster create, change the following line to use driver name for
        # loading.
        return driver.DriverManager("magnum.drivers",
                                    driver_info['entry_point_name']).driver()

    @classmethod
    def get_driver_for_cluster(cls, context, cluster):
        ct = cluster_template.ClusterTemplate.get_by_uuid(
            context, cluster.cluster_template_id)
        return cls.get_driver(ct.server_type, ct.cluster_distro, ct.coe)

    def update_cluster_status(self, context, cluster, use_admin_ctx=False):
        """Update the cluster status based on underlying orchestration

           This is an optional method if your implementation does not need
           to poll the orchestration for status updates (for example, your
           driver uses some notification-based mechanism instead).
        """
        return

    @abc.abstractproperty
    def provides(self):
        """return a list of (server_type, os, coe) tuples

           Returns a list of cluster configurations supported by this driver
        """
        raise NotImplementedError("Subclasses must implement 'provides'.")

    @abc.abstractmethod
    def create_cluster(self, context, cluster, cluster_create_timeout):
        raise NotImplementedError("Subclasses must implement "
                                  "'create_cluster'.")

    @abc.abstractmethod
    def update_cluster(self, context, cluster, scale_manager=None,
                       rollback=False):
        raise NotImplementedError("Subclasses must implement "
                                  "'update_cluster'.")

    def pre_delete_cluster(self, context, cluster):
        """Delete cloud resources before deleting the cluster.

        Specific driver could implement this method as needed.
        """
        return None

    @abc.abstractmethod
    def upgrade_cluster(self, context, cluster, cluster_template,
                        max_batch_size, nodegroup, scale_manager=None,
                        rollback=False):
        raise NotImplementedError("Subclasses must implement "
                                  "'upgrade_cluster'.")

    @abc.abstractmethod
    def delete_cluster(self, context, cluster):
        raise NotImplementedError("Subclasses must implement "
                                  "'delete_cluster'.")

    @abc.abstractmethod
    def resize_cluster(self, context, cluster, resize_manager,
                       node_count, nodes_to_remove, nodegroup=None):
        raise NotImplementedError("Subclasses must implement "
                                  "'resize_cluster'.")

    @abc.abstractmethod
    def create_federation(self, context, federation):
        raise NotImplementedError("Subclasses must implement "
                                  "'create_federation'.")

    @abc.abstractmethod
    def update_federation(self, context, federation):
        raise NotImplementedError("Subclasses must implement "
                                  "'update_federation'.")

    @abc.abstractmethod
    def delete_federation(self, context, federation):
        raise NotImplementedError("Subclasses must implement "
                                  "'delete_federation'.")

    @abc.abstractmethod
    def create_nodegroup(self, context, cluster, nodegroup):
        raise NotImplementedError("Subclasses must implement "
                                  "'create_nodegroup'.")

    @abc.abstractmethod
    def update_nodegroup(self, context, cluster, nodegroup):
        raise NotImplementedError("Subclasses must implement "
                                  "'update_nodegroup'.")

    @abc.abstractmethod
    def delete_nodegroup(self, context, cluster, nodegroup):
        raise NotImplementedError("Subclasses must implement "
                                  "'delete_nodegroup'.")

    def get_monitor(self, context, cluster):
        """return the monitor with container data for this driver."""

        return None

    def get_scale_manager(self, context, osclient, cluster):
        """return the scale manager for this driver."""

        return None

    def rotate_ca_certificate(self, context, cluster):
        raise exception.NotSupported(
            "'rotate_ca_certificate' is not supported by this driver.")
