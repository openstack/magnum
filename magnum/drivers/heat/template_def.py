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

from oslo_log import log as logging
from oslo_utils import strutils
import re
import requests
import six
from six.moves.urllib import parse as urlparse

from magnum.common import clients
from magnum.common import exception
from magnum.common import keystone
from magnum.common import utils
import magnum.conf

from requests import exceptions as req_exceptions

LOG = logging.getLogger(__name__)

COMMON_TEMPLATES_PATH = "../../common/templates/"
COMMON_ENV_PATH = COMMON_TEMPLATES_PATH + "environments/"

CONF = magnum.conf.CONF


class ParameterMapping(object):
    """A mapping associating heat param and cluster_template attr.

    A ParameterMapping is an association of a Heat parameter name with
    an attribute on a Cluster, ClusterTemplate, or both.

    In the case of both cluster_template_attr and cluster_attr being set, the
    ClusterTemplate will be checked first and then Cluster if the attribute
    isn't set on the ClusterTemplate.

    Parameters can also be set as 'required'. If a required parameter
    isn't set, a RequiredArgumentNotProvided exception will be raised.
    """
    def __init__(self, heat_param, cluster_template_attr=None,
                 cluster_attr=None, required=False,
                 param_type=lambda x: x):
        self.heat_param = heat_param
        self.cluster_template_attr = cluster_template_attr
        self.cluster_attr = cluster_attr
        self.required = required
        self.param_type = param_type

    def set_param(self, params, cluster_template, cluster):
        value = None

        if (self.cluster_template_attr and
                getattr(cluster_template, self.cluster_template_attr, None)
                is not None):
            value = getattr(cluster_template, self.cluster_template_attr)
        elif (self.cluster_attr and
                getattr(cluster, self.cluster_attr, None) is not None):
            value = getattr(cluster, self.cluster_attr)
        elif self.required:
            kwargs = dict(heat_param=self.heat_param)
            raise exception.RequiredParameterNotProvided(**kwargs)

        if value is not None:
            value = self.param_type(value)
            params[self.heat_param] = value


class OutputMapping(object):
    """A mapping associating heat outputs and cluster attr.

    An OutputMapping is an association of a Heat output with a key
    Magnum understands.
    """

    def __init__(self, heat_output, cluster_attr=None):
        self.cluster_attr = cluster_attr
        self.heat_output = heat_output

    def set_output(self, stack, cluster_template, cluster):
        if self.cluster_attr is None:
            return

        output_value = self.get_output_value(stack)
        if output_value is not None:
            setattr(cluster, self.cluster_attr, output_value)

    def matched(self, output_key):
        return self.heat_output == output_key

    def get_output_value(self, stack):
        for output in stack.to_dict().get('outputs', []):
            if output['output_key'] == self.heat_output:
                return output['output_value']

        LOG.warning('stack does not have output_key %s', self.heat_output)
        return None


@six.add_metaclass(abc.ABCMeta)
class TemplateDefinition(object):
    """A mapping between Magnum objects and Heat templates.

    A TemplateDefinition is essentially a mapping between Magnum objects
    and Heat templates. Each TemplateDefinition has a mapping of Heat
    parameters.
    """

    def __init__(self):
        self.param_mappings = list()
        self.output_mappings = list()

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

    def get_params(self, context, cluster_template, cluster, **kwargs):
        """Pulls template parameters from ClusterTemplate.

        :param context: Context to pull template parameters for
        :param cluster_template: ClusterTemplate to pull template parameters
         from
        :param cluster: Cluster to pull template parameters from
        :param extra_params: Any extra params to be provided to the template

        :return: dict of template parameters
        """
        template_params = dict()

        for mapping in self.param_mappings:
            mapping.set_param(template_params, cluster_template, cluster)

        if 'extra_params' in kwargs:
            template_params.update(kwargs.get('extra_params'))

        return template_params

    def get_env_files(self, cluster_template, cluster):
        """Gets stack environment files based upon ClusterTemplate attributes.

        Base implementation returns no files (empty list). Meant to be
        overridden by subclasses.

        :param cluster_template: ClusterTemplate to grab environment files for

        :return: list of relative paths to environment files
        """
        return []

    def get_heat_param(self, cluster_attr=None, cluster_template_attr=None):
        """Returns stack param name.

        Return stack param name using cluster and cluster_template attributes
        :param cluster_attr: cluster attribute from which it maps to stack
         attribute
        :param cluster_template_attr: cluster_template attribute from which it
         maps to stack attribute

        :return: stack parameter name or None
        """
        for mapping in self.param_mappings:
            if (mapping.cluster_attr == cluster_attr and
                    mapping.cluster_template_attr == cluster_template_attr):
                return mapping.heat_param

        return None

    def update_outputs(self, stack, cluster_template, cluster):
        for output in self.output_mappings:
            output.set_output(stack, cluster_template, cluster)

    @abc.abstractproperty
    def driver_module_path(self):
        pass

    @abc.abstractproperty
    def template_path(self):
        pass

    def extract_definition(self, context, cluster_template, cluster, **kwargs):
        return (self.template_path,
                self.get_params(context, cluster_template, cluster, **kwargs),
                self.get_env_files(cluster_template, cluster))


class BaseTemplateDefinition(TemplateDefinition):
    def __init__(self):
        super(BaseTemplateDefinition, self).__init__()
        self._osc = None

        self.add_parameter('ssh_key_name',
                           cluster_attr='keypair')
        self.add_parameter('server_image',
                           cluster_template_attr='image_id')
        self.add_parameter('dns_nameserver',
                           cluster_template_attr='dns_nameserver')
        self.add_parameter('http_proxy',
                           cluster_template_attr='http_proxy')
        self.add_parameter('https_proxy',
                           cluster_template_attr='https_proxy')
        self.add_parameter('no_proxy',
                           cluster_template_attr='no_proxy')
        self.add_parameter('number_of_masters',
                           cluster_attr='master_count')

    @property
    def driver_module_path(self):
        pass

    @abc.abstractproperty
    def template_path(self):
        pass

    def get_osc(self, context):
        if not self._osc:
            self._osc = clients.OpenStackClients(context)
        return self._osc

    def get_params(self, context, cluster_template, cluster, **kwargs):
        osc = self.get_osc(context)

        extra_params = kwargs.pop('extra_params', {})
        extra_params['trustee_domain_id'] = osc.keystone().trustee_domain_id
        extra_params['trustee_user_id'] = cluster.trustee_user_id
        extra_params['trustee_username'] = cluster.trustee_username
        extra_params['trustee_password'] = cluster.trustee_password
        extra_params['verify_ca'] = CONF.drivers.verify_ca
        extra_params['openstack_ca'] = utils.get_openstack_ca()

        # Only pass trust ID into the template if allowed by the config file
        if CONF.trust.cluster_user_trust:
            extra_params['trust_id'] = cluster.trust_id
        else:
            extra_params['trust_id'] = ""

        kwargs = {
            'service_type': 'identity',
            'interface': CONF.trust.trustee_keystone_interface,
            'version': 3
        }
        if CONF.trust.trustee_keystone_region_name:
            kwargs['region_name'] = CONF.trust.trustee_keystone_region_name
        extra_params['auth_url'] = osc.url_for(**kwargs).rstrip('/')

        return super(BaseTemplateDefinition,
                     self).get_params(context, cluster_template, cluster,
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
            LOG.error(err)
            raise exception.GetClusterSizeFailed(
                discovery_url=discovery_url)

        try:
            result = ast.literal_eval(result)
        except (ValueError, SyntaxError):
            raise exception.InvalidClusterDiscoveryURL(
                discovery_url=discovery_url)

        node_value = result.get('node', None)
        if node_value is None:
            raise exception.InvalidClusterDiscoveryURL(
                discovery_url=discovery_url)

        value = node_value.get('value', None)
        if value is None:
            raise exception.InvalidClusterDiscoveryURL(
                discovery_url=discovery_url)
        elif int(value) != expect_size:
            raise exception.InvalidClusterSize(
                expect_size=expect_size,
                size=int(value),
                discovery_url=discovery_url)

    def get_proxies(self, url, cluster_template):
        proxies = dict()
        if cluster_template is None:
            return proxies
        hostname = urlparse.urlparse(url).netloc.partition(":")[0]
        if hasattr(cluster_template, 'no_proxy') and \
            cluster_template.no_proxy and \
            (cluster_template.no_proxy == '*' or
             re.search('\\b%s\\b' % re.escape(hostname),
                       cluster_template.no_proxy, re.I)):
            LOG.debug('Bypass proxy, because discovery hostname is listed in'
                      ' cluster template no_proxy variable')
        else:
            if hasattr(cluster_template, 'http_proxy'):
                proxies['http'] = cluster_template.http_proxy
            if hasattr(cluster_template, 'https_proxy'):
                proxies['https'] = cluster_template.https_proxy
        return proxies

    def get_discovery_url(self, cluster, cluster_template=None):
        if hasattr(cluster, 'discovery_url') and cluster.discovery_url:
            if getattr(cluster, 'master_count', None) is not None:
                self.validate_discovery_url(cluster.discovery_url,
                                            cluster.master_count)
            else:
                self.validate_discovery_url(cluster.discovery_url, 1)
            discovery_url = cluster.discovery_url
        else:
            discovery_endpoint = (
                CONF.cluster.etcd_discovery_service_endpoint_format %
                {'size': cluster.master_count})
            try:
                proxies = self.get_proxies(discovery_endpoint,
                                           cluster_template)
                discovery_request = requests.get(discovery_endpoint,
                                                 proxies=proxies)
                if discovery_request.status_code != requests.codes.ok:
                    raise exception.GetDiscoveryUrlFailed(
                        discovery_endpoint=discovery_endpoint)
                discovery_url = discovery_request.text
            except req_exceptions.RequestException as err:
                LOG.error(err)
                raise exception.GetDiscoveryUrlFailed(
                    discovery_endpoint=discovery_endpoint)
            if not discovery_url:
                raise exception.InvalidDiscoveryURL(
                    discovery_url=discovery_url,
                    discovery_endpoint=discovery_endpoint)
            else:
                cluster.discovery_url = discovery_url
        return discovery_url

    def get_scale_params(self, context, cluster, scale_manager=None):
        return dict()


def add_lb_env_file(env_files, cluster_template):
    if cluster_template.master_lb_enabled:
        if keystone.is_octavia_enabled():
            env_files.append(COMMON_ENV_PATH + 'with_master_lb_octavia.yaml')
        else:
            env_files.append(COMMON_ENV_PATH + 'with_master_lb.yaml')
    else:
        env_files.append(COMMON_ENV_PATH + 'no_master_lb.yaml')


def add_volume_env_file(env_files, cluster):
    if cluster.docker_volume_size is None:
        env_files.append(COMMON_ENV_PATH + 'no_volume.yaml')
    else:
        env_files.append(COMMON_ENV_PATH + 'with_volume.yaml')


def add_etcd_volume_env_file(env_files, cluster_template):
    if int(cluster_template.labels.get('etcd_volume_size', 0)) < 1:
        env_files.append(COMMON_ENV_PATH + 'no_etcd_volume.yaml')
    else:
        env_files.append(COMMON_ENV_PATH + 'with_etcd_volume.yaml')


def add_fip_env_file(env_files, cluster_template, cluster):
    lb_fip_enabled = cluster.labels.get(
        "master_lb_floating_ip_enabled",
        cluster_template.floating_ip_enabled
    )
    master_lb_fip_enabled = strutils.bool_from_string(lb_fip_enabled)

    if cluster_template.floating_ip_enabled:
        env_files.append(COMMON_ENV_PATH + 'enable_floating_ip.yaml')
    else:
        env_files.append(COMMON_ENV_PATH + 'disable_floating_ip.yaml')

    if cluster_template.master_lb_enabled and master_lb_fip_enabled:
        env_files.append(COMMON_ENV_PATH + 'enable_lb_floating_ip.yaml')
    else:
        env_files.append(COMMON_ENV_PATH + 'disable_lb_floating_ip.yaml')


def add_priv_net_env_file(env_files, cluster_template):
    if cluster_template.fixed_network:
        env_files.append(COMMON_ENV_PATH + 'no_private_network.yaml')
    else:
        env_files.append(COMMON_ENV_PATH + 'with_private_network.yaml')
