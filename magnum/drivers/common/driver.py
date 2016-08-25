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

import os

from heatclient.common import template_utils
from oslo_config import cfg
from oslo_log import log as logging
from pkg_resources import iter_entry_points
from stevedore import driver

from magnum.common import exception
from magnum.common import short_id
from magnum.conductor import utils as conductor_utils


CONF = cfg.CONF
LOG = logging.getLogger(__name__)


def _extract_template_definition(context, cluster, scale_manager=None):
    cluster_template = conductor_utils.retrieve_cluster_template(context,
                                                                 cluster)
    cluster_driver = Driver().get_driver(cluster_template.server_type,
                                         cluster_template.cluster_distro,
                                         cluster_template.coe)
    definition = cluster_driver.get_template_definition()
    return definition.extract_definition(context, cluster_template, cluster,
                                         scale_manager=scale_manager)


def _get_env_files(template_path, env_rel_paths):
    template_dir = os.path.dirname(template_path)
    env_abs_paths = [os.path.join(template_dir, f) for f in env_rel_paths]
    environment_files = []
    env_map, merged_env = (
        template_utils.process_multiple_environments_and_files(
            env_paths=env_abs_paths, env_list_tracker=environment_files))
    return environment_files, env_map


class Driver(object):
    definitions = None
    provides = list()

    @classmethod
    def load_entry_points(cls):
        for entry_point in iter_entry_points('magnum.drivers'):
            yield entry_point, entry_point.load(require=False)

    @classmethod
    def get_drivers(cls):
        '''Retrieves cluster drivers from python entry_points.

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
        '''

        if not cls.definitions:
            cls.definitions = dict()
            for entry_point, def_class in cls.load_entry_points():
                for cluster_type in def_class.provides:
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
        '''Get Driver.

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
        '''

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

    def create_stack(self, context, osc, cluster, cluster_create_timeout):
        template_path, heat_params, env_files = (
            _extract_template_definition(context, cluster))

        tpl_files, template = template_utils.get_template_contents(
            template_path)

        environment_files, env_map = _get_env_files(template_path, env_files)
        tpl_files.update(env_map)

        # Make sure no duplicate stack name
        stack_name = '%s-%s' % (cluster.name, short_id.generate_id())
        if cluster_create_timeout:
            heat_timeout = cluster_create_timeout
        else:
            # no cluster_create_timeout value was passed in to the request
            # so falling back on configuration file value
            heat_timeout = cfg.CONF.cluster_heat.create_timeout
        fields = {
            'stack_name': stack_name,
            'parameters': heat_params,
            'environment_files': environment_files,
            'template': template,
            'files': tpl_files,
            'timeout_mins': heat_timeout
        }
        created_stack = osc.heat().stacks.create(**fields)

        return created_stack

    def update_stack(self, context, osc, cluster, scale_manager=None,
                     rollback=False):
        template_path, heat_params, env_files = _extract_template_definition(
            context, cluster, scale_manager=scale_manager)

        tpl_files, template = template_utils.get_template_contents(
            template_path)
        environment_files, env_map = _get_env_files(template_path, env_files)
        tpl_files.update(env_map)

        fields = {
            'parameters': heat_params,
            'environment_files': environment_files,
            'template': template,
            'files': tpl_files,
            'disable_rollback': not rollback
        }

        return osc.heat().stacks.update(cluster.stack_id, **fields)
