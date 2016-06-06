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

KUBE_SECURE_PORT = '6443'
KUBE_INSECURE_PORT = '8080'
DOCKER_PORT = '2376'

template_def_opts = [
    cfg.StrOpt('k8s_atomic_template_path',
               default=paths.basedir_def('templates/kubernetes/'
                                         'kubecluster.yaml'),
               deprecated_name='template_path',
               deprecated_group='bay_heat',
               help=_(
                   'Location of template to build a k8s cluster on atomic.')),
    cfg.StrOpt('k8s_coreos_template_path',
               default=paths.basedir_def('templates/kubernetes/'
                                         'kubecluster-coreos.yaml'),
               help=_(
                   'Location of template to build a k8s cluster on CoreOS.')),
    cfg.StrOpt('etcd_discovery_service_endpoint_format',
               default='https://discovery.etcd.io/new?size=%(size)d',
               help=_('Url for etcd public discovery endpoint.')),
    cfg.StrOpt('swarm_atomic_template_path',
               default=paths.basedir_def('templates/swarm/'
                                         'swarmcluster.yaml'),
               help=_('Location of template to build a swarm '
                      'cluster on atomic.')),
    cfg.StrOpt('mesos_ubuntu_template_path',
               default=paths.basedir_def('templates/mesos/'
                                         'mesoscluster.yaml'),
               help=_('Location of template to build a Mesos cluster '
                      'on Ubuntu.')),
    cfg.ListOpt('enabled_definitions',
                default=['magnum_vm_atomic_k8s', 'magnum_vm_coreos_k8s',
                         'magnum_vm_atomic_swarm', 'magnum_vm_ubuntu_mesos'],
                help=_('Enabled bay definition entry points.')),
]

docker_registry_opts = [
    cfg.StrOpt('swift_region',
               help=_('Region name of Swift')),
    cfg.StrOpt('swift_registry_container',
               default='docker_registry',
               help=_('Name of the container in Swift which docker registry '
                      'stores images in'))
]

CONF = cfg.CONF
CONF.register_opts(template_def_opts, group='bay')
CONF.register_opts(docker_registry_opts, group='docker_registry')


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

    def set_output(self, stack, baymodel, bay):
        if self.bay_attr is None:
            return

        output_value = self.get_output_value(stack)
        if output_value is not None:
            setattr(bay, self.bay_attr, output_value)

    def matched(self, output_key):
        return self.heat_output == output_key

    def get_output_value(self, stack):
        for output in stack.to_dict().get('outputs', []):
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
        mapping_type = kwargs.pop('mapping_type', OutputMapping)
        output = mapping_type(*args, **kwargs)
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

    def update_outputs(self, stack, baymodel, bay):
        for output in self.output_mappings:
            output.set_output(stack, baymodel, bay)

    @abc.abstractproperty
    def template_path(self):
        pass

    def extract_definition(self, context, baymodel, bay, **kwargs):
        return self.template_path, self.get_params(context, baymodel, bay,
                                                   **kwargs)


class BaseTemplateDefinition(TemplateDefinition):
    def __init__(self):
        super(BaseTemplateDefinition, self).__init__()
        self._osc = None

        self.add_parameter('ssh_key_name',
                           baymodel_attr='keypair_id',
                           required=True)
        self.add_parameter('server_image',
                           baymodel_attr='image_id')
        self.add_parameter('dns_nameserver',
                           baymodel_attr='dns_nameserver')
        self.add_parameter('http_proxy',
                           baymodel_attr='http_proxy')
        self.add_parameter('https_proxy',
                           baymodel_attr='https_proxy')
        self.add_parameter('no_proxy',
                           baymodel_attr='no_proxy')
        self.add_parameter('number_of_masters',
                           bay_attr='master_count')

    @abc.abstractproperty
    def template_path(self):
        pass

    def get_osc(self, context):
        if not self._osc:
            self._osc = clients.OpenStackClients(context)
        return self._osc

    def get_params(self, context, baymodel, bay, **kwargs):
        osc = self.get_osc(context)

        extra_params = kwargs.pop('extra_params', {})
        extra_params['trustee_domain_id'] = osc.keystone().trustee_domain_id
        extra_params['trustee_user_id'] = bay.trustee_user_id
        extra_params['trustee_username'] = bay.trustee_username
        extra_params['trustee_password'] = bay.trustee_password
        extra_params['trust_id'] = bay.trust_id
        extra_params['auth_url'] = context.auth_url

        return super(BaseTemplateDefinition,
                     self).get_params(context, baymodel, bay,
                                      extra_params=extra_params,
                                      **kwargs)

    def get_discovery_url(self, bay):
        if hasattr(bay, 'discovery_url') and bay.discovery_url:
            discovery_url = bay.discovery_url
        else:
            discovery_endpoint = (
                cfg.CONF.bay.etcd_discovery_service_endpoint_format %
                {'size': bay.master_count})
            try:
                discovery_url = requests.get(discovery_endpoint).text
            except Exception as err:
                LOG.error(six.text_type(err))
                raise exception.GetDiscoveryUrlFailed(
                    discovery_endpoint=discovery_endpoint)
            if not discovery_url:
                raise exception.InvalidDiscoveryURL(
                    discovery_url=discovery_url,
                    discovery_endpoint=discovery_endpoint)
            else:
                bay.discovery_url = discovery_url
        return discovery_url


class K8sApiAddressOutputMapping(OutputMapping):

    def set_output(self, stack, baymodel, bay):
        # TODO(yuanying): port number is hardcoded, this will be fix
        protocol = 'https'
        port = KUBE_SECURE_PORT
        if baymodel.tls_disabled:
            protocol = 'http'
            port = KUBE_INSECURE_PORT

        output_value = self.get_output_value(stack)
        params = {
            'protocol': protocol,
            'address': output_value,
            'port': port,
        }
        output_value = "%(protocol)s://%(address)s:%(port)s" % params

        if output_value is not None:
            setattr(bay, self.bay_attr, output_value)


class SwarmApiAddressOutputMapping(OutputMapping):

    def set_output(self, stack, baymodel, bay):
        protocol = 'https'
        if baymodel.tls_disabled:
            protocol = 'tcp'

        output_value = self.get_output_value(stack)
        params = {
            'protocol': protocol,
            'address': output_value,
            'port': DOCKER_PORT,
        }
        output_value = "%(protocol)s://%(address)s:%(port)s" % params

        if output_value is not None:
            setattr(bay, self.bay_attr, output_value)


class K8sTemplateDefinition(BaseTemplateDefinition):
    """Base Kubernetes template."""

    def __init__(self):
        super(K8sTemplateDefinition, self).__init__()
        self.add_parameter('master_flavor',
                           baymodel_attr='master_flavor_id')
        self.add_parameter('minion_flavor',
                           baymodel_attr='flavor_id')
        self.add_parameter('number_of_minions',
                           bay_attr='node_count')
        self.add_parameter('external_network',
                           baymodel_attr='external_network_id',
                           required=True)
        self.add_parameter('network_driver',
                           baymodel_attr='network_driver')
        self.add_parameter('volume_driver',
                           baymodel_attr='volume_driver')
        self.add_parameter('tls_disabled',
                           baymodel_attr='tls_disabled',
                           required=True)
        self.add_parameter('registry_enabled',
                           baymodel_attr='registry_enabled')
        self.add_parameter('bay_uuid',
                           bay_attr='uuid',
                           param_type=str)
        self.add_parameter('insecure_registry_url',
                           baymodel_attr='insecure_registry')

        self.add_output('api_address',
                        bay_attr='api_address',
                        mapping_type=K8sApiAddressOutputMapping)
        self.add_output('kube_minions_private',
                        bay_attr=None)
        self.add_output('kube_minions',
                        bay_attr='node_addresses')
        self.add_output('kube_masters_private',
                        bay_attr=None)
        self.add_output('kube_masters',
                        bay_attr='master_addresses')

    def get_params(self, context, baymodel, bay, **kwargs):
        extra_params = kwargs.pop('extra_params', {})
        scale_mgr = kwargs.pop('scale_manager', None)
        if scale_mgr:
            hosts = self.get_output('kube_minions')
            extra_params['minions_to_remove'] = (
                scale_mgr.get_removal_nodes(hosts))

        extra_params['discovery_url'] = self.get_discovery_url(bay)
        osc = self.get_osc(context)
        extra_params['magnum_url'] = osc.magnum_url()

        if baymodel.tls_disabled:
            extra_params['loadbalancing_protocol'] = 'HTTP'
            extra_params['kubernetes_port'] = 8080

        label_list = ['flannel_network_cidr', 'flannel_backend',
                      'flannel_network_subnetlen']
        for label in label_list:
            extra_params[label] = baymodel.labels.get(label)

        if baymodel.registry_enabled:
            extra_params['swift_region'] = CONF.docker_registry.swift_region
            extra_params['registry_container'] = (
                CONF.docker_registry.swift_registry_container)

        return super(K8sTemplateDefinition,
                     self).get_params(context, baymodel, bay,
                                      extra_params=extra_params,
                                      **kwargs)


class AtomicK8sTemplateDefinition(K8sTemplateDefinition):
    """Kubernetes template for a Fedora Atomic VM."""

    provides = [
        {'server_type': 'vm',
         'os': 'fedora-atomic',
         'coe': 'kubernetes'},
    ]

    def __init__(self):
        super(AtomicK8sTemplateDefinition, self).__init__()
        self.add_parameter('docker_volume_size',
                           baymodel_attr='docker_volume_size')
        self.add_parameter('docker_storage_driver',
                           baymodel_attr='docker_storage_driver')

    def get_params(self, context, baymodel, bay, **kwargs):
        extra_params = kwargs.pop('extra_params', {})

        extra_params['username'] = context.user_name
        extra_params['tenant_name'] = context.tenant
        osc = self.get_osc(context)
        extra_params['region_name'] = osc.cinder_region_name()

        return super(AtomicK8sTemplateDefinition,
                     self).get_params(context, baymodel, bay,
                                      extra_params=extra_params,
                                      **kwargs)

    @property
    def template_path(self):
        return cfg.CONF.bay.k8s_atomic_template_path


class CoreOSK8sTemplateDefinition(K8sTemplateDefinition):
    """Kubernetes template for CoreOS VM."""

    provides = [
        {'server_type': 'vm', 'os': 'coreos', 'coe': 'kubernetes'},
    ]

    @property
    def template_path(self):
        return cfg.CONF.bay.k8s_coreos_template_path


class AtomicSwarmTemplateDefinition(BaseTemplateDefinition):
    """Docker swarm template for a Fedora Atomic VM."""

    provides = [
        {'server_type': 'vm', 'os': 'fedora-atomic', 'coe': 'swarm'},
    ]

    def __init__(self):
        super(AtomicSwarmTemplateDefinition, self).__init__()
        self.add_parameter('bay_uuid',
                           bay_attr='uuid',
                           param_type=str)
        self.add_parameter('number_of_nodes',
                           bay_attr='node_count')
        self.add_parameter('master_flavor',
                           baymodel_attr='master_flavor_id')
        self.add_parameter('node_flavor',
                           baymodel_attr='flavor_id')
        self.add_parameter('docker_volume_size',
                           baymodel_attr='docker_volume_size')
        self.add_parameter('external_network',
                           baymodel_attr='external_network_id',
                           required=True)
        self.add_parameter('network_driver',
                           baymodel_attr='network_driver')
        self.add_parameter('tls_disabled',
                           baymodel_attr='tls_disabled',
                           required=True)
        self.add_parameter('registry_enabled',
                           baymodel_attr='registry_enabled')
        self.add_parameter('docker_storage_driver',
                           baymodel_attr='docker_storage_driver')
        self.add_output('api_address',
                        bay_attr='api_address',
                        mapping_type=SwarmApiAddressOutputMapping)
        self.add_output('swarm_master_private',
                        bay_attr=None)
        self.add_output('swarm_masters',
                        bay_attr='master_addresses')
        self.add_output('swarm_nodes_private',
                        bay_attr=None)
        self.add_output('swarm_nodes',
                        bay_attr='node_addresses')
        self.add_output('discovery_url',
                        bay_attr='discovery_url')

    def get_params(self, context, baymodel, bay, **kwargs):
        extra_params = kwargs.pop('extra_params', {})
        extra_params['discovery_url'] = self.get_discovery_url(bay)
        # HACK(apmelton) - This uses the user's bearer token, ideally
        # it should be replaced with an actual trust token with only
        # access to do what the template needs it to do.
        osc = self.get_osc(context)
        extra_params['magnum_url'] = osc.magnum_url()

        label_list = ['flannel_network_cidr', 'flannel_backend',
                      'flannel_network_subnetlen']

        for label in label_list:
            extra_params[label] = baymodel.labels.get(label)

        if baymodel.registry_enabled:
            extra_params['swift_region'] = CONF.docker_registry.swift_region
            extra_params['registry_container'] = (
                CONF.docker_registry.swift_registry_container)

        return super(AtomicSwarmTemplateDefinition,
                     self).get_params(context, baymodel, bay,
                                      extra_params=extra_params,
                                      **kwargs)

    @property
    def template_path(self):
        return cfg.CONF.bay.swarm_atomic_template_path


class UbuntuMesosTemplateDefinition(BaseTemplateDefinition):
    """Mesos template for Ubuntu VM."""

    provides = [
        {'server_type': 'vm', 'os': 'ubuntu', 'coe': 'mesos'},
    ]

    def __init__(self):
        super(UbuntuMesosTemplateDefinition, self).__init__()
        self.add_parameter('external_network',
                           baymodel_attr='external_network_id',
                           required=True)
        self.add_parameter('number_of_slaves',
                           bay_attr='node_count')
        self.add_parameter('master_flavor',
                           baymodel_attr='master_flavor_id')
        self.add_parameter('slave_flavor',
                           baymodel_attr='flavor_id')
        self.add_parameter('cluster_name',
                           bay_attr='name')
        self.add_parameter('volume_driver',
                           baymodel_attr='volume_driver')

        self.add_output('api_address',
                        bay_attr='api_address')
        self.add_output('mesos_master_private',
                        bay_attr=None)
        self.add_output('mesos_master',
                        bay_attr='master_addresses')
        self.add_output('mesos_slaves_private',
                        bay_attr=None)
        self.add_output('mesos_slaves',
                        bay_attr='node_addresses')

    def get_params(self, context, baymodel, bay, **kwargs):
        extra_params = kwargs.pop('extra_params', {})
        # HACK(apmelton) - This uses the user's bearer token, ideally
        # it should be replaced with an actual trust token with only
        # access to do what the template needs it to do.
        osc = self.get_osc(context)
        extra_params['auth_url'] = context.auth_url
        extra_params['username'] = context.user_name
        extra_params['tenant_name'] = context.tenant
        extra_params['domain_name'] = context.domain_name
        extra_params['region_name'] = osc.cinder_region_name()

        label_list = ['rexray_preempt', 'mesos_slave_isolation',
                      'mesos_slave_image_providers',
                      'mesos_slave_work_dir',
                      'mesos_slave_executor_env_variables']

        for label in label_list:
            extra_params[label] = baymodel.labels.get(label)

        return super(UbuntuMesosTemplateDefinition,
                     self).get_params(context, baymodel, bay,
                                      extra_params=extra_params,
                                      **kwargs)

    @property
    def template_path(self):
        return cfg.CONF.bay.mesos_ubuntu_template_path
