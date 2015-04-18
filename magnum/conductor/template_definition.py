# Copyright 2014 Rackspace Inc. All rights reserved.
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
import uuid

from oslo_config import cfg
from pkg_resources import iter_entry_points
import requests
import six

from magnum.common import exception
from magnum.openstack.common._i18n import _

from magnum.common import paths


template_def_opts = [
    cfg.StrOpt('k8s_atomic_template_path',
               default=paths.basedir_def('templates/heat-kubernetes/'
                                         'kubecluster.yaml'),
               deprecated_name='template_path',
               deprecated_group='k8s_heat',
               help=_(
                   'Location of template to build a k8s cluster on atomic. ')),
    cfg.StrOpt('k8s_coreos_template_path',
               default=paths.basedir_def('templates/heat-kubernetes/'
                                         'kubecluster-coreos.yaml'),
               help=_(
                   'Location of template to build a k8s cluster on coreos. ')),
    cfg.StrOpt('coreos_discovery_token_url',
               default=None,
               deprecated_name='discovery_token_url',
               deprecated_group='k8s_heat',
               help=_('coreos discovery token url.')),
    cfg.StrOpt('swarm_atomic_template_path',
               default=paths.basedir_def('templates/docker-swarm/'
                                         'swarm.yaml'),
               help=_('Location of template to build a swarm '
                      'cluster on atomic. ')),
    cfg.StrOpt('swarm_discovery_url_format',
               default=None,
               help=_('Format string to use for swarm discovery url. '
                      'Available values: bay_id, bay_uuid. '
                      'Example: "etcd://etcd.example.com/\%(bay_uuid)s" ')),
    cfg.BoolOpt('public_swarm_discovery',
                default=True,
                help=_('Indicates Swarm discovery should use public '
                       'endpoint.')),
    cfg.StrOpt('public_swarm_discovery_url',
               default='https://discovery-stage.hub.docker.com/v1/clusters',
               help=_('Url for swarm public discovery endpoint.')),
    cfg.ListOpt('enabled_definitions',
                default=['magnum_vm_atomic_k8s', 'magnum_vm_coreos_k8s',
                         'magnum_vm_atomic_swarm'],
                help=_('Enabled bay definition entry points. ')),
]

cfg.CONF.register_opts(template_def_opts, group='bay')


class ParameterMapping(object):
    """A ParameterMapping is an association of a Heat parameter name with
    an attribute on a Bay, Baymodel, or both.

    In the case of both baymodel_attr and bay_attr being set, the Baymodel
    will be checked first and then Bay if the attribute isn't set on the
    Baymodel.

    Parameters can also be set as 'required'. If a required parameter
    isn't set, a RequiredArgumentNotProvided exception will be raised.
    """
    def __init__(self, heat_param, baymodel_attr=None,
                 bay_attr=None, required=False,
                 param_type=lambda x: x):
        self.heat_param = heat_param
        self.baymodel_attr = baymodel_attr
        self.bay_attr = bay_attr
        self.required = required
        self.param_type = param_type

    def set_param(self, params, baymodel, bay):
        value = None

        if (self.baymodel_attr and
                getattr(baymodel, self.baymodel_attr, None)):
            value = getattr(baymodel, self.baymodel_attr)
        elif (self.bay_attr and
                getattr(bay, self.bay_attr, None)):
            value = getattr(bay, self.bay_attr)
        elif self.required:
            kwargs = dict(heat_param=self.heat_param)
            raise exception.RequiredParameterNotProvided(**kwargs)

        if value:
            value = self.param_type(value)
            params[self.heat_param] = value


class OutputMapping(object):
    """An OutputMapping is an association of a Heat output with a key
    Magnum understands.
    """

    def __init__(self, heat_output, bay_attr=None):
        self.bay_attr = bay_attr
        self.heat_output = heat_output

    def set_output(self, stack, bay):
        for output in stack.outputs:
            if output['output_key'] == self.heat_output:
                setattr(bay, self.bay_attr, output['output_value'])
                break


@six.add_metaclass(abc.ABCMeta)
class TemplateDefinition(object):
    '''A TemplateDefinition is essentially a mapping between Magnum objects
    and Heat templates. Each TemplateDefinition has a mapping of Heat
    parameters.
    '''
    definitions = None
    provides = list()

    def __init__(self):
        self.param_mappings = list()
        self.output_mappings = list()

    @staticmethod
    def load_entry_points():
        for entry_point in iter_entry_points('magnum.template_definitions'):
            yield entry_point, entry_point.load(require=False)

    @classmethod
    def get_template_definitions(cls):
        '''Retrieves bay definitions from python entry_points.

        Example:

        With the following classes:
        class TemplateDefinition1(TemplateDefinition):
            provides = [
                ('platform1', 'os1', 'coe1')
            ]

        class TemplateDefinition2(TemplateDefinition):
            provides = [
                ('platform2', 'os2', 'coe2')
            ]

        And the following entry_points:

        magnum.template_definitions =
            template_name_1 = some.python.path:TemplateDefinition1
            template_name_2 = some.python.path:TemplateDefinition2

        get_template_definitions will return:
            {
                (platform1, os1, coe1):
                    {'template_name_1': TemplateDefinition1},
                (platform2, os2, coe2):
                    {'template_name_2': TemplateDefinition2}
            }

        :return: dict
        '''

        if not cls.definitions:
            cls.definitions = dict()
            for entry_point, def_class in cls.load_entry_points():
                for bay_type in def_class.provides:
                    bay_type_tuple = (bay_type['platform'],
                                      bay_type['os'],
                                      bay_type['coe'])
                    providers = cls.definitions.setdefault(bay_type_tuple,
                                                           dict())
                    providers[entry_point.name] = def_class

        return cls.definitions

    @classmethod
    def get_template_definition(cls, platform, os, coe):
        '''Returns the enabled TemplateDefinition class for the provided
        bay_type.

        With the following classes:
        class TemplateDefinition1(TemplateDefinition):
            provides = [
                ('platform1', 'os1', 'coe1')
            ]

        class TemplateDefinition2(TemplateDefinition):
            provides = [
                ('platform2', 'os2', 'coe2')
            ]

        And the following entry_points:

        magnum.template_definitions =
            template_name_1 = some.python.path:TemplateDefinition1
            template_name_2 = some.python.path:TemplateDefinition2

        get_template_name_1_definition('platform2', 'os2', 'coe2')
        will return: TemplateDefinition2

        :param platform: The platform the bay definition will build on
        :param os: The operation system the bay definition will build on
        :param coe: The Container Orchestration Environment the bay will
                    produce

        :return: class
        '''

        definition_map = cls.get_template_definitions()
        bay_type = (platform, os, coe)

        if bay_type not in definition_map:
            raise exception.BayTypeNotSupported(platform=platform, os=os,
                                                coe=coe)
        type_definitions = definition_map[bay_type]

        for name in cfg.CONF.bay.enabled_definitions:
            if name in type_definitions:
                return type_definitions[name]()

        raise exception.BayTypeNotEnabled(platform=platform, os=os, coe=coe)

    def add_parameter(self, *args, **kwargs):
        param = ParameterMapping(*args, **kwargs)
        self.param_mappings.append(param)

    def add_output(self, *args, **kwargs):
        output = OutputMapping(*args, **kwargs)
        self.output_mappings.append(output)

    def get_params(self, baymodel, bay, extra_params=None):
        """Pulls template parameters from Baymodel and Bay.

        :param baymodel: Baymodel to pull template parameters from
        :param bay: Bay to pull template parameters from
        :param extra_params: Any extra params to provide to the template

        :return: dict of template parameters
        """
        template_params = dict()

        for mapping in self.param_mappings:
            mapping.set_param(template_params, baymodel, bay)

        if extra_params:
            template_params.update(extra_params)

        return template_params

    def update_outputs(self, stack, bay):
        for output in self.output_mappings:
            output.set_output(stack, bay)

    @abc.abstractproperty
    def template_path(self):
        pass

    def extract_definition(self, baymodel, bay, extra_params=None):
        return self.template_path, self.get_params(baymodel, bay,
                                                   extra_params=extra_params)


class BaseTemplateDefinition(TemplateDefinition):
    def __init__(self):
        super(BaseTemplateDefinition, self).__init__()
        self.add_parameter('ssh_key_name',
                           baymodel_attr='keypair_id',
                           required=True)
        self.add_parameter('external_network_id',
                           baymodel_attr='external_network_id',
                           required=True)

        self.add_parameter('server_image',
                           baymodel_attr='image_id')
        self.add_parameter('server_flavor',
                           baymodel_attr='flavor_id')
        self.add_parameter('dns_nameserver',
                           baymodel_attr='dns_nameserver')

    @abc.abstractproperty
    def template_path(self):
        pass


class AtomicK8sTemplateDefinition(BaseTemplateDefinition):
    provides = [
        {'platform': 'vm', 'os': 'fedora-atomic', 'coe': 'kubernetes'},
    ]

    def __init__(self):
        super(AtomicK8sTemplateDefinition, self).__init__()
        self.add_parameter('master_flavor',
                           baymodel_attr='master_flavor_id')
        self.add_parameter('fixed_network',
                           baymodel_attr='fixed_network')
        self.add_parameter('number_of_minions',
                           bay_attr='node_count',
                           param_type=str)
        self.add_parameter('docker_volume_size',
                           baymodel_attr='docker_volume_size')
        # TODO(yuanying): Add below lines if apiserver_port parameter
        # is supported
        # self.add_parameter('apiserver_port',
        #                    baymodel_attr='apiserver_port')

        self.add_output('kube_master',
                        bay_attr='api_address')
        self.add_output('kube_minions_external',
                        bay_attr='node_addresses')

    @property
    def template_path(self):
        return cfg.CONF.bay.k8s_atomic_template_path


class CoreOSK8sTemplateDefinition(AtomicK8sTemplateDefinition):
    provides = [
        {'platform': 'vm', 'os': 'coreos', 'coe': 'kubernetes'},
    ]

    def __init__(self):
        super(CoreOSK8sTemplateDefinition, self).__init__()
        self.add_parameter('ssh_authorized_key',
                           baymodel_attr='ssh_authorized_key')

    @staticmethod
    def get_token():
        discovery_url = cfg.CONF.bay.coreos_discovery_token_url
        if discovery_url:
            coreos_token_url = requests.get(discovery_url)
            token = str(coreos_token_url.text.split('/')[3])
        else:
            token = uuid.uuid4().hex
        return token

    def get_params(self, baymodel, bay, extra_params=None):
        if not extra_params:
            extra_params = dict()

        extra_params['token'] = self.get_token()

        return super(CoreOSK8sTemplateDefinition,
                     self).get_params(baymodel, bay, extra_params=extra_params)

    @property
    def template_path(self):
        return cfg.CONF.bay.k8s_coreos_template_path


class AtomicSwarmTemplateDefinition(BaseTemplateDefinition):
    provides = [
        {'platform': 'vm', 'os': 'fedora-atomic', 'coe': 'swarm'},
    ]

    def __init__(self):
        super(AtomicSwarmTemplateDefinition, self).__init__()
        self.add_parameter('number_of_nodes',
                           bay_attr='node_count',
                           param_type=str)
        self.add_parameter('fixed_network_cidr',
                           baymodel_attr='fixed_network')

        self.add_output('swarm_manager',
                        bay_attr='api_address')
        self.add_output('swarm_nodes_external',
                        bay_attr='node_addresses')
        self.add_output('discovery_url',
                        bay_attr='discovery_url')

    @staticmethod
    def get_public_token():
        token_id = requests.post(cfg.CONF.bay.public_swarm_discovery_url).text
        return 'token://%s' % token_id

    @staticmethod
    def parse_discovery_url(bay):
        strings = dict(bay_id=bay.id, bay_uuid=bay.uuid)
        return cfg.CONF.bay.swarm_discovery_url_format % strings

    def get_discovery_url(self, bay):
        if hasattr(bay, 'discovery_url') and bay.discovery_url:
            discovery_url = bay.discovery_url
        elif cfg.CONF.bay.public_swarm_discovery:
            discovery_url = self.get_public_token()
        else:
            discovery_url = self.parse_discovery_url(bay)

        return discovery_url

    def get_params(self, baymodel, bay, extra_params=None):
        if not extra_params:
            extra_params = dict()

        extra_params['discovery_url'] = self.get_discovery_url(bay)

        return super(AtomicSwarmTemplateDefinition,
                     self).get_params(baymodel, bay, extra_params=extra_params)

    @property
    def template_path(self):
        return cfg.CONF.bay.swarm_atomic_template_path
