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
from oslo_log import log as logging
from pkg_resources import iter_entry_points
import requests
import six

from magnum.common import clients
from magnum.common import exception
from magnum.common import paths
from magnum.i18n import _
from magnum.i18n import _LW


LOG = logging.getLogger(__name__)


template_def_opts = [
    cfg.StrOpt('k8s_atomic_template_path',
               default=paths.basedir_def('templates/heat-kubernetes/'
                                         'kubecluster.yaml'),
               deprecated_name='template_path',
               deprecated_group='bay_heat',
               help=_(
                   'Location of template to build a k8s cluster on atomic.')),
    cfg.StrOpt('k8s_coreos_template_path',
               default=paths.basedir_def('templates/heat-kubernetes/'
                                         'kubecluster-coreos.yaml'),
               help=_(
                   'Location of template to build a k8s cluster on CoreOS.')),
    cfg.StrOpt('etcd_discovery_service_endpoint_format',
               default='https://discovery.etcd.io/new?size=%(size)d',
               help=_('Url for etcd public discovery endpoint.')),
    cfg.StrOpt('coreos_discovery_token_url',
               default=None,
               deprecated_name='discovery_token_url',
               deprecated_group='bay_heat',
               help=_('coreos discovery token url.')),
    cfg.StrOpt('swarm_atomic_template_path',
               default=paths.basedir_def('templates/docker-swarm/'
                                         'swarm.yaml'),
               help=_('Location of template to build a swarm '
                      'cluster on atomic.')),
    cfg.StrOpt('swarm_discovery_url_format',
               default=None,
               help=_('Format string to use for swarm discovery url. '
                      'Available values: bay_id, bay_uuid. '
                      'Example: "etcd://etcd.example.com/\%(bay_uuid)s"')),
    cfg.BoolOpt('public_swarm_discovery',
                default=True,
                help=_('Indicates Swarm discovery should use public '
                       'endpoint.')),
    cfg.StrOpt('public_swarm_discovery_url',
               default='https://discovery.hub.docker.com/v1/clusters',
               help=_('Url for swarm public discovery endpoint.')),
    cfg.StrOpt('mesos_ubuntu_template_path',
               default=paths.basedir_def('templates/heat-mesos/'
                                         'mesoscluster.yaml'),
               help=_('Location of template to build a Mesos cluster '
                      'on Ubuntu.')),
    cfg.ListOpt('enabled_definitions',
                default=['magnum_vm_atomic_k8s', 'magnum_vm_coreos_k8s',
                         'magnum_vm_atomic_swarm', 'magnum_vm_ubuntu_mesos'],
                help=_('Enabled bay definition entry points.')),
]

cfg.CONF.register_opts(template_def_opts, group='bay')


class ParameterMapping(object):
    """A mapping associating heat param and bay/baymodel attr.

    A ParameterMapping is an association of a Heat parameter name with
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
                getattr(baymodel, self.baymodel_attr, None) is not None):
            value = getattr(baymodel, self.baymodel_attr)
        elif (self.bay_attr and
                getattr(bay, self.bay_attr, None) is not None):
            value = getattr(bay, self.bay_attr)
        elif self.required:
            kwargs = dict(heat_param=self.heat_param)
            raise exception.RequiredParameterNotProvided(**kwargs)

        if value is not None:
            value = self.param_type(value)
            params[self.heat_param] = value


class OutputMapping(object):
    """A mapping associating heat outputs and bay attr.

    An OutputMapping is an association of a Heat output with a key
    Magnum understands.
    """

    def __init__(self, heat_output, bay_attr=None):
        self.bay_attr = bay_attr
        self.heat_output = heat_output

    def set_output(self, stack, bay):
        if self.bay_attr is None:
            return

        output_value = self.get_output_value(stack)
        if output_value is not None:
            setattr(bay, self.bay_attr, output_value)

    def matched(self, output_key):
        return self.heat_output == output_key

    def get_output_value(self, stack):
        for output in stack.outputs:
            if output['output_key'] == self.heat_output:
                return output['output_value']

        LOG.warning(_LW('stack does not have output_key %s'), self.heat_output)
        return None


@six.add_metaclass(abc.ABCMeta)
class TemplateDefinition(object):
    '''A mapping between Magnum objects and Heat templates.

    A TemplateDefinition is essentially a mapping between Magnum objects
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
                ('server_type1', 'os1', 'coe1')
            ]

        class TemplateDefinition2(TemplateDefinition):
            provides = [
                ('server_type2', 'os2', 'coe2')
            ]

        And the following entry_points:

        magnum.template_definitions =
            template_name_1 = some.python.path:TemplateDefinition1
            template_name_2 = some.python.path:TemplateDefinition2

        get_template_definitions will return:
            {
                (server_type1, os1, coe1):
                    {'template_name_1': TemplateDefinition1},
                (server_type2, os2, coe2):
                    {'template_name_2': TemplateDefinition2}
            }

        :return: dict
        '''

        if not cls.definitions:
            cls.definitions = dict()
            for entry_point, def_class in cls.load_entry_points():
                for bay_type in def_class.provides:
                    bay_type_tuple = (bay_type['server_type'],
                                      bay_type['os'],
                                      bay_type['coe'])
                    providers = cls.definitions.setdefault(bay_type_tuple,
                                                           dict())
                    providers[entry_point.name] = def_class

        return cls.definitions

    @classmethod
    def get_template_definition(cls, server_type, os, coe):
        '''Get enabled TemplateDefinitions.

        Returns the enabled TemplateDefinition class for the provided
        bay_type.

        With the following classes:
        class TemplateDefinition1(TemplateDefinition):
            provides = [
                ('server_type1', 'os1', 'coe1')
            ]

        class TemplateDefinition2(TemplateDefinition):
            provides = [
                ('server_type2', 'os2', 'coe2')
            ]

        And the following entry_points:

        magnum.template_definitions =
            template_name_1 = some.python.path:TemplateDefinition1
            template_name_2 = some.python.path:TemplateDefinition2

        get_template_name_1_definition('server_type2', 'os2', 'coe2')
        will return: TemplateDefinition2

        :param server_type: The server_type the bay definition
                                   will build on
        :param os: The operation system the bay definition will build on
        :param coe: The Container Orchestration Environment the bay will
                    produce

        :return: class
        '''

        definition_map = cls.get_template_definitions()
        bay_type = (server_type, os, coe)

        if bay_type not in definition_map:
            raise exception.BayTypeNotSupported(
                server_type=server_type,
                os=os,
                coe=coe)
        type_definitions = definition_map[bay_type]

        for name in cfg.CONF.bay.enabled_definitions:
            if name in type_definitions:
                return type_definitions[name]()

        raise exception.BayTypeNotEnabled(
            server_type=server_type, os=os, coe=coe)

    def add_parameter(self, *args, **kwargs):
        param = ParameterMapping(*args, **kwargs)
        self.param_mappings.append(param)

    def add_output(self, *args, **kwargs):
        output = OutputMapping(*args, **kwargs)
        self.output_mappings.append(output)

    def get_output(self, *args, **kwargs):
        for output in self.output_mappings:
            if output.matched(*args, **kwargs):
                return output

        return None

    def get_params(self, context, baymodel, bay, **kwargs):
        """Pulls template parameters from Baymodel and/or Bay.

        :param context: Context to pull template parameters for
        :param baymodel: Baymodel to pull template parameters from
        :param bay: Bay to pull template parameters from
        :param extra_params: Any extra params to be provided to the template

        :return: dict of template parameters
        """
        template_params = dict()

        for mapping in self.param_mappings:
            mapping.set_param(template_params, baymodel, bay)

        if 'extra_params' in kwargs:
            template_params.update(kwargs.get('extra_params'))

        return template_params

    def get_heat_param(self, bay_attr=None, baymodel_attr=None):
        """Returns stack param name.

        Return stack param name using bay and baymodel attributes
        :param bay_attr bay attribute from which it maps to stack attribute
        :param baymodel_attr baymodel attribute from which it maps
         to stack attribute

        :return stack parameter name or None
        """
        for mapping in self.param_mappings:
            if (mapping.bay_attr == bay_attr and
                    mapping.baymodel_attr == baymodel_attr):
                return mapping.heat_param

        return None

    def update_outputs(self, stack, bay):
        for output in self.output_mappings:
            output.set_output(stack, bay)

    @abc.abstractproperty
    def template_path(self):
        pass

    def extract_definition(self, context, baymodel, bay, **kwargs):
        return self.template_path, self.get_params(context, baymodel, bay,
                                                   **kwargs)


class BaseTemplateDefinition(TemplateDefinition):
    def __init__(self):
        super(BaseTemplateDefinition, self).__init__()
        self.add_parameter('ssh_key_name',
                           baymodel_attr='keypair_id',
                           required=True)
        self.add_parameter('server_image',
                           baymodel_attr='image_id')
        self.add_parameter('dns_nameserver',
                           baymodel_attr='dns_nameserver')
        self.add_parameter('fixed_network_cidr',
                           baymodel_attr='fixed_network')
        self.add_parameter('http_proxy',
                           baymodel_attr='http_proxy')
        self.add_parameter('https_proxy',
                           baymodel_attr='https_proxy')
        self.add_parameter('no_proxy',
                           baymodel_attr='no_proxy')

    @abc.abstractproperty
    def template_path(self):
        pass


class AtomicK8sTemplateDefinition(BaseTemplateDefinition):
    provides = [
        {'server_type': 'vm',
         'os': 'fedora-atomic',
         'coe': 'kubernetes'},
    ]

    def __init__(self):
        super(AtomicK8sTemplateDefinition, self).__init__()
        self.add_parameter('master_flavor',
                           baymodel_attr='master_flavor_id')
        self.add_parameter('minion_flavor',
                           baymodel_attr='flavor_id')
        self.add_parameter('number_of_minions',
                           bay_attr='node_count',
                           param_type=str)
        self.add_parameter('number_of_masters',
                           bay_attr='master_count',
                           param_type=str)
        self.add_parameter('docker_volume_size',
                           baymodel_attr='docker_volume_size')
        self.add_parameter('external_network',
                           baymodel_attr='external_network_id',
                           required=True)
        self.add_parameter('network_driver',
                           baymodel_attr='network_driver')
        # TODO(yuanying): Add below lines if apiserver_port parameter
        # is supported
        # self.add_parameter('apiserver_port',
        #                    baymodel_attr='apiserver_port')

        self.add_output('api_address',
                        bay_attr='api_address')
        self.add_output('kube_minions',
                        bay_attr=None)
        self.add_output('kube_minions_external',
                        bay_attr='node_addresses')

    def get_discovery_url(self, bay):
        if hasattr(bay, 'discovery_url') and bay.discovery_url:
            discovery_url = bay.discovery_url
        else:
            discovery_endpoint = (
                cfg.CONF.bay.etcd_discovery_service_endpoint_format %
                {'size': bay.master_count})
            discovery_url = requests.get(discovery_endpoint).text
            if not discovery_url:
                raise exception.InvalidDiscoveryURL(
                    discovery_url=discovery_url,
                    discovery_endpoint=discovery_endpoint)
            else:
                bay.discovery_url = discovery_url
        return discovery_url

    def get_params(self, context, baymodel, bay, **kwargs):
        extra_params = kwargs.pop('extra_params', {})
        label_list = ['flannel_network_cidr', 'flannel_use_vxlan',
                      'flannel_network_subnetlen']
        scale_mgr = kwargs.pop('scale_manager', None)
        if scale_mgr:
            hosts = self.get_output('kube_minions')
            extra_params['minions_to_remove'] = (
                scale_mgr.get_removal_nodes(hosts))

        extra_params['discovery_url'] = self.get_discovery_url(bay)

        for label in label_list:
            extra_params[label] = baymodel.labels.get(label)

        return super(AtomicK8sTemplateDefinition,
                     self).get_params(context, baymodel, bay,
                                      extra_params=extra_params,
                                      **kwargs)

    @property
    def template_path(self):
        return cfg.CONF.bay.k8s_atomic_template_path


class CoreOSK8sTemplateDefinition(AtomicK8sTemplateDefinition):
    provides = [
        {'server_type': 'vm', 'os': 'coreos', 'coe': 'kubernetes'},
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

    def get_params(self, context, baymodel, bay, **kwargs):
        extra_params = kwargs.pop('extra_params', {})
        extra_params['token'] = self.get_token()

        return super(CoreOSK8sTemplateDefinition,
                     self).get_params(context, baymodel, bay,
                                      extra_params=extra_params,
                                      **kwargs)

    @property
    def template_path(self):
        return cfg.CONF.bay.k8s_coreos_template_path


class AtomicSwarmTemplateDefinition(BaseTemplateDefinition):
    provides = [
        {'server_type': 'vm', 'os': 'fedora-atomic', 'coe': 'swarm'},
    ]

    def __init__(self):
        super(AtomicSwarmTemplateDefinition, self).__init__()
        self.add_parameter('bay_uuid',
                           bay_attr='uuid',
                           param_type=str)
        self.add_parameter('number_of_nodes',
                           bay_attr='node_count',
                           param_type=str)
        self.add_parameter('server_flavor',
                           baymodel_attr='flavor_id')
        self.add_parameter('external_network',
                           baymodel_attr='external_network_id',
                           required=True)
        self.add_parameter('tls_disabled',
                           baymodel_attr='tls_disabled',
                           required=True)
        self.add_output('swarm_master',
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

    def get_params(self, context, baymodel, bay, **kwargs):
        extra_params = kwargs.pop('extra_params', {})
        extra_params['discovery_url'] = self.get_discovery_url(bay)
        # HACK(apmelton) - This uses the user's bearer token, ideally
        # it should be replaced with an actual trust token with only
        # access to do what the template needs it to do.
        extra_params['user_token'] = context.auth_token
        osc = clients.OpenStackClients(context)
        extra_params['magnum_url'] = osc.magnum_url()

        return super(AtomicSwarmTemplateDefinition,
                     self).get_params(context, baymodel, bay,
                                      extra_params=extra_params,
                                      **kwargs)

    @property
    def template_path(self):
        return cfg.CONF.bay.swarm_atomic_template_path


class UbuntuMesosTemplateDefinition(BaseTemplateDefinition):
    provides = [
        {'server_type': 'vm', 'os': 'ubuntu', 'coe': 'mesos'},
    ]

    def __init__(self):
        super(UbuntuMesosTemplateDefinition, self).__init__()
        self.add_parameter('external_network',
                           baymodel_attr='external_network_id',
                           required=True)
        self.add_parameter('number_of_slaves',
                           bay_attr='node_count',
                           param_type=str)
        self.add_parameter('master_flavor',
                           baymodel_attr='master_flavor_id')
        self.add_parameter('slave_flavor',
                           baymodel_attr='flavor_id')

        self.add_output('mesos_master',
                        bay_attr='api_address')
        self.add_output('mesos_slaves',
                        bay_attr='node_addresses')

    @property
    def template_path(self):
        return cfg.CONF.bay.mesos_ubuntu_template_path
