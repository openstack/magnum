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
from oslo_utils import uuidutils
import requests
import six

from magnum.common import clients
from magnum.common import exception
from magnum.common import keystone
from magnum.common import nova
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
                 cluster_attr=None, required=False, param_type=lambda x: x):
        self.heat_param = heat_param
        self.cluster_template_attr = cluster_template_attr
        self.cluster_attr = cluster_attr
        self.required = required
        self.param_type = param_type

    def set_param(self, params, cluster_template, cluster):
        value = self.get_value(cluster_template, cluster)
        if self.required and value is None:
            kwargs = dict(heat_param=self.heat_param)
            raise exception.RequiredParameterNotProvided(**kwargs)

        if value is not None:
            value = self.param_type(value)
            params[self.heat_param] = value

    def get_value(self, cluster_template, cluster):
        value = None
        if (self.cluster_template_attr and
                getattr(cluster_template, self.cluster_template_attr, None)
                is not None):
            value = getattr(cluster_template, self.cluster_template_attr)
        elif (self.cluster_attr and
                getattr(cluster, self.cluster_attr, None) is not None):
            value = getattr(cluster, self.cluster_attr)
        return value


class NodeGroupParameterMapping(ParameterMapping):

    def __init__(self, heat_param, nodegroup_attr=None, nodegroup_uuid=None,
                 required=False, param_type=lambda x: x):
        self.heat_param = heat_param
        self.nodegroup_attr = nodegroup_attr
        self.nodegroup_uuid = nodegroup_uuid
        self.required = required
        self.param_type = param_type

    def get_value(self, cluster_template, cluster):
        value = None
        for ng in cluster.nodegroups:
            if ng.uuid == self.nodegroup_uuid and self.nodegroup_attr in ng:
                value = getattr(ng, self.nodegroup_attr)
                break
        return value


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

        output_value = self.get_output_value(stack, cluster)
        if output_value is None:
            return
        setattr(cluster, self.cluster_attr, output_value)

    def matched(self, output_key):
        return self.heat_output == output_key

    def get_output_value(self, stack, cluster):
        for output in stack.to_dict().get('outputs', []):
            if output['output_key'] == self.heat_output:
                return output['output_value']

        LOG.debug('cluster %(cluster_uuid)s, status %(cluster_status)s, '
                  'stack %(stack_id)s does not have output_key '
                  '%(heat_output)s',
                  {'cluster_uuid': cluster.uuid,
                   'cluster_status': cluster.status,
                   'stack_id': stack.id,
                   'heat_output': self.heat_output}
                  )
        return None


class NodeGroupOutputMapping(OutputMapping):
    """A mapping associating stack info and nodegroup attr.

    A NodeGroupOutputMapping is an association of a Heat output or parameter
    with a nodegroup field. By default stack output values are reflected to the
    specified nodegroup attribute. In the case where is_stack_param is set to
    True, the specified heat information will come from the stack parameters.
    """
    def __init__(self, heat_output, nodegroup_attr=None, nodegroup_uuid=None,
                 is_stack_param=False):
        self.nodegroup_attr = nodegroup_attr
        self.nodegroup_uuid = nodegroup_uuid
        self.heat_output = heat_output
        self.is_stack_param = is_stack_param

    def set_output(self, stack, cluster_template, cluster):
        if self.nodegroup_attr is None:
            return

        output_value = self.get_output_value(stack, cluster)
        if output_value is None:
            return

        for ng in cluster.nodegroups:
            if ng.uuid == self.nodegroup_uuid:
                # nodegroups are fetched from the database every
                # time, so the bad thing here is that we need to
                # save each change.
                previous_value = getattr(ng, self.nodegroup_attr, None)
                if previous_value == output_value:
                    # Avoid saving if it's not needed.
                    return
                setattr(ng, self.nodegroup_attr, output_value)
                ng.save()

    def get_output_value(self, stack, cluster):
        if not self.is_stack_param:
            return super(NodeGroupOutputMapping, self).get_output_value(
                stack, cluster)
        return self.get_param_value(stack)

    def get_param_value(self, stack):
        for param, value in stack.parameters.items():
            if param == self.heat_output:
                return value

        LOG.warning('stack does not have param %s', self.heat_output)
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
        self.nodegroup_output_mappings = list()

    def add_parameter(self, *args, **kwargs):
        param_class = kwargs.pop('param_class', ParameterMapping)
        param = param_class(*args, **kwargs)
        self.param_mappings.append(param)

    def add_output(self, *args, **kwargs):
        mapping_type = kwargs.pop('mapping_type', OutputMapping)
        output = mapping_type(*args, **kwargs)
        if kwargs.get('cluster_attr', None):
            self.output_mappings.append(output)
        else:
            self.nodegroup_output_mappings.append(output)

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

    def get_env_files(self, cluster_template, cluster, nodegroup=None):
        """Gets stack environment files based upon ClusterTemplate attributes.

        Base implementation returns no files (empty list). Meant to be
        overridden by subclasses.

        :param cluster_template: ClusterTemplate to grab environment files for

        :return: list of relative paths to environment files
        """
        return []

    def get_heat_param(self, cluster_attr=None, cluster_template_attr=None,
                       nodegroup_attr=None, nodegroup_uuid=None):
        """Returns stack param name.

        Return stack param name using cluster and cluster_template attributes
        :param cluster_attr: cluster attribute from which it maps to stack
         attribute
        :param cluster_template_attr: cluster_template attribute from which it
         maps to stack attribute

        :return: stack parameter name or None
        """
        for mapping in self.param_mappings:
            if hasattr(mapping, 'cluster_attr'):
                if mapping.cluster_attr == cluster_attr and \
                        mapping.cluster_template_attr == cluster_template_attr:
                    return mapping.heat_param
            if hasattr(mapping, 'nodegroup_attr'):
                if mapping.nodegroup_attr == nodegroup_attr and \
                        mapping.nodegroup_uuid == nodegroup_uuid:
                    return mapping.heat_param

        return None

    def get_stack_diff(self, context, heat_params, cluster):
        """Returns all the params that are changed.

        Compares the current params of a stack with the template def for
        the cluster and return the ones that changed.
        :param heat_params: a dict containing the current params and values
         for a stack
        :param cluster: the cluster we need to compare with.
        """
        diff = {}
        for mapping in self.param_mappings:
            try:
                heat_param_name = mapping.heat_param
                stack_value = heat_params[heat_param_name]
                value = mapping.get_value(cluster.cluster_template, cluster)
                if value is None:
                    continue
                # We need to avoid changing the param values if it's not
                # necessary, so for some attributes we need to resolve the
                # value either to name or uuid.
                value = self.resolve_ambiguous_values(context, heat_param_name,
                                                      stack_value, value)
                if stack_value != value:
                    diff.update({heat_param_name: value})
            except KeyError:
                # If the key is not in heat_params just skip it. In case
                # of update we don't want to trigger a rebuild....
                continue
        return diff

    def resolve_ambiguous_values(self, context, heat_param, heat_value, value):
        return str(value)

    def add_nodegroup_params(self, cluster, nodegroups=None):
        pass

    def update_outputs(self, stack, cluster_template, cluster,
                       nodegroups=None):
        for output in self.output_mappings:
            output.set_output(stack, cluster_template, cluster)
        for output in self.nodegroup_output_mappings:
            output.set_output(stack, cluster_template, cluster)

    @abc.abstractproperty
    def driver_module_path(self):
        pass

    @abc.abstractproperty
    def template_path(self):
        pass

    def extract_definition(self, context, cluster_template, cluster, **kwargs):
        nodegroups_list = kwargs.get('nodegroups', None)
        nodegroup = None if not nodegroups_list else nodegroups_list[0]
        return (self.template_path,
                self.get_params(context, cluster_template, cluster, **kwargs),
                self.get_env_files(cluster_template, cluster,
                                   nodegroup=nodegroup))


class BaseTemplateDefinition(TemplateDefinition):
    def __init__(self):
        super(BaseTemplateDefinition, self).__init__()
        self._osc = None

        self.add_parameter('ssh_key_name',
                           cluster_attr='keypair')
        self.add_parameter('dns_nameserver',
                           cluster_template_attr='dns_nameserver')
        self.add_parameter('http_proxy',
                           cluster_template_attr='http_proxy')
        self.add_parameter('https_proxy',
                           cluster_template_attr='https_proxy')
        self.add_parameter('no_proxy',
                           cluster_template_attr='no_proxy')

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

        nodegroups = kwargs.pop('nodegroups', None)
        # Add all the params from the cluster's nodegroups
        self.add_nodegroup_params(cluster, nodegroups=nodegroups)

        extra_params = kwargs.pop('extra_params', {})
        extra_params['trustee_domain_id'] = osc.keystone().trustee_domain_id
        extra_params['trustee_user_id'] = cluster.trustee_user_id
        extra_params['trustee_username'] = cluster.trustee_username
        extra_params['trustee_password'] = cluster.trustee_password
        extra_params['verify_ca'] = CONF.drivers.verify_ca
        extra_params['openstack_ca'] = utils.get_openstack_ca()
        ssh_public_key = nova.get_ssh_key(context, cluster.keypair)
        if ssh_public_key != "":
            extra_params['ssh_public_key'] = ssh_public_key

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
        # NOTE: Sometimes, version discovery fails when Magnum cannot talk to
        # Keystone via specified trustee_keystone_interface intended for
        # cluster instances either because it is not unreachable from the
        # controller or CA certs are missing for TLS enabled interface and the
        # returned auth_url may not be suffixed with /v3 in which case append
        # the url with the suffix so that instances can still talk to Keystone.
        auth_url = osc.url_for(**kwargs).rstrip('/')
        extra_params['auth_url'] = auth_url + ('' if auth_url.endswith('/v3')
                                               else '/v3')

        return super(BaseTemplateDefinition,
                     self).get_params(context, cluster_template, cluster,
                                      extra_params=extra_params,
                                      **kwargs)

    def resolve_ambiguous_values(self, context, heat_param, heat_value, value):
        # Ambiguous values should be converted to the same format.
        osc = self.get_osc(context)
        if heat_param == 'external_network':
            network = osc.neutron().show_network(heat_value).get('network')
            if uuidutils.is_uuid_like(heat_value):
                value = network.get('id')
            else:
                value = network('name')
        # Any other values we might need to resolve?
        return super(BaseTemplateDefinition, self).resolve_ambiguous_values(
            context, heat_param, heat_value, value)

    def add_nodegroup_params(self, cluster, nodegroups=None):
        master_params, worker_params = self.get_nodegroup_param_maps()
        nodegroups = nodegroups or [cluster.default_ng_worker,
                                    cluster.default_ng_master]
        for nodegroup in nodegroups:
            params = worker_params
            if nodegroup.role == 'master':
                params = master_params
            self._handle_nodegroup_param_map(nodegroup, params)

    def get_nodegroup_param_maps(self, master_params=None, worker_params=None):
        master_params = master_params or dict()
        worker_params = worker_params or dict()
        master_params.update({
            'number_of_masters': 'node_count',
        })
        return master_params, worker_params

    def _handle_nodegroup_param_map(self, nodegroup, param_map):
        for template_attr, nodegroup_attr in param_map.items():
            self.add_parameter(template_attr, nodegroup_attr=nodegroup_attr,
                               nodegroup_uuid=nodegroup.uuid,
                               param_class=NodeGroupParameterMapping)

    def _get_relevant_labels(self, cluster, kwargs):
        nodegroups = kwargs.get('nodegroups', None)
        labels = cluster.labels
        if nodegroups is not None:
            labels = nodegroups[0].labels
        return labels

    def update_outputs(self, stack, cluster_template, cluster,
                       nodegroups=None):
        master_ng = cluster.default_ng_master
        nodegroups = nodegroups or [cluster.default_ng_master]
        for nodegroup in nodegroups:
            if nodegroup.role == 'master':
                self.add_output('number_of_masters',
                                nodegroup_attr='node_count',
                                nodegroup_uuid=master_ng.uuid,
                                is_stack_param=True,
                                mapping_type=NodeGroupOutputMapping)
        super(BaseTemplateDefinition,
              self).update_outputs(stack, cluster_template, cluster,
                                   nodegroups=nodegroups)

    def validate_discovery_url(self, discovery_url, expect_size):
        url = str(discovery_url)
        if url[len(url)-1] == '/':
            url += '_config/size'
        else:
            url += '/_config/size'

        try:
            result = requests.get(url, timeout=60).text
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

    def get_discovery_url(self, cluster):
        if hasattr(cluster, 'discovery_url') and cluster.discovery_url:
            # NOTE(flwang): The discovery URl does have a expiry time,
            # so better skip it when the cluster has been created.
            if not cluster.master_addresses:
                self.validate_discovery_url(cluster.discovery_url,
                                            cluster.master_count)
            discovery_url = cluster.discovery_url
        else:
            discovery_endpoint = (
                CONF.cluster.etcd_discovery_service_endpoint_format %
                {'size': cluster.master_count})
            try:
                discovery_request = requests.get(discovery_endpoint,
                                                 timeout=60)
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


def add_lb_env_file(env_files, cluster):
    if cluster.master_lb_enabled:
        if keystone.is_octavia_enabled():
            env_files.append(COMMON_ENV_PATH + 'with_master_lb_octavia.yaml')
        else:
            env_files.append(COMMON_ENV_PATH + 'with_master_lb.yaml')
    else:
        env_files.append(COMMON_ENV_PATH + 'no_master_lb.yaml')


def add_volume_env_file(env_files, cluster, nodegroup=None):
    if nodegroup:
        docker_volume_size = nodegroup.docker_volume_size
    else:
        docker_volume_size = cluster.docker_volume_size
    if docker_volume_size is None:
        env_files.append(COMMON_ENV_PATH + 'no_volume.yaml')
    else:
        env_files.append(COMMON_ENV_PATH + 'with_volume.yaml')


def add_etcd_volume_env_file(env_files, cluster):
    if int(cluster.labels.get('etcd_volume_size', 0)) < 1:
        env_files.append(COMMON_ENV_PATH + 'no_etcd_volume.yaml')
    else:
        env_files.append(COMMON_ENV_PATH + 'with_etcd_volume.yaml')


def add_fip_env_file(env_files, cluster):
    lb_fip_enabled = cluster.labels.get("master_lb_floating_ip_enabled")
    master_lb_fip_enabled = (strutils.bool_from_string(lb_fip_enabled) or
                             cluster.floating_ip_enabled)

    if cluster.floating_ip_enabled:
        env_files.append(COMMON_ENV_PATH + 'enable_floating_ip.yaml')
    else:
        env_files.append(COMMON_ENV_PATH + 'disable_floating_ip.yaml')

    if cluster.master_lb_enabled and master_lb_fip_enabled:
        env_files.append(COMMON_ENV_PATH + 'enable_lb_floating_ip.yaml')
    else:
        env_files.append(COMMON_ENV_PATH + 'disable_lb_floating_ip.yaml')


def add_priv_net_env_file(env_files, cluster_template, cluster):
    if (cluster.fixed_network or cluster_template.fixed_network):
        env_files.append(COMMON_ENV_PATH + 'no_private_network.yaml')
    else:
        env_files.append(COMMON_ENV_PATH + 'with_private_network.yaml')
