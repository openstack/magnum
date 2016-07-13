# Copyright 2016 Rackspace Inc. All rights reserved.
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
import ast

from oslo_config import cfg
from oslo_log import log as logging
from pkg_resources import iter_entry_points
import requests
import six

from magnum.common import clients
from magnum.common import exception
from magnum.i18n import _
from magnum.i18n import _LW

from requests import exceptions as req_exceptions


LOG = logging.getLogger(__name__)


template_def_opts = [
    cfg.StrOpt('etcd_discovery_service_endpoint_format',
               default='https://discovery.etcd.io/new?size=%(size)d',
               help=_('Url for etcd public discovery endpoint.')),
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
CONF.import_opt('trustee_domain_id', 'magnum.common.keystone', group='trust')


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
        :param os: The operating system the bay definition will build on
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

    def get_env_files(self, baymodel):
        """Collects stack environment files based upon Baymodel attributes.

        Base implementation returns no files (empty list). Meant to be
        overridden by subclasses.

        :param baymodel: Baymodel to collect environment files for

        :return: list of relative paths to environment files
        """
        return []

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
        return (self.template_path,
                self.get_params(context, baymodel, bay, **kwargs),
                self.get_env_files(baymodel))


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

    def validate_discovery_url(self, discovery_url, expect_size):
        url = str(discovery_url)
        if url[len(url)-1] == '/':
            url += '_config/size'
        else:
            url += '/_config/size'

        try:
            result = requests.get(url).text
        except req_exceptions.RequestException as err:
            LOG.error(six.text_type(err))
            raise exception.GetClusterSizeFailed(
                discovery_url=discovery_url)

        try:
            result = ast.literal_eval(result)
        except (ValueError, SyntaxError):
            raise exception.InvalidBayDiscoveryURL(
                discovery_url=discovery_url)

        node_value = result.get('node', None)
        if node_value is None:
            raise exception.InvalidBayDiscoveryURL(
                discovery_url=discovery_url)

        value = node_value.get('value', None)
        if value is None:
            raise exception.InvalidBayDiscoveryURL(
                discovery_url=discovery_url)
        elif int(value) != expect_size:
            raise exception.InvalidClusterSize(
                expect_size=expect_size,
                size=int(value),
                discovery_url=discovery_url)

    def get_discovery_url(self, bay):
        if hasattr(bay, 'discovery_url') and bay.discovery_url:
            if getattr(bay, 'master_count', None) is not None:
                self.validate_discovery_url(bay.discovery_url,
                                            bay.master_count)
            else:
                self.validate_discovery_url(bay.discovery_url, 1)
            discovery_url = bay.discovery_url
        else:
            discovery_endpoint = (
                cfg.CONF.bay.etcd_discovery_service_endpoint_format %
                {'size': bay.master_count})
            try:
                discovery_url = requests.get(discovery_endpoint).text
            except req_exceptions.RequestException as err:
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
