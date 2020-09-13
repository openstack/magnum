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

from magnum.drivers.heat import template_def
from oslo_config import cfg
from oslo_log import log as logging

CONF = cfg.CONF
DOCKER_PORT = '2375'

LOG = logging.getLogger(__name__)


class SwarmModeApiAddressOutputMapping(template_def.OutputMapping):

    def set_output(self, stack, cluster_template, cluster):
        if self.cluster_attr is None:
            return

        output_value = self.get_output_value(stack, cluster)
        if output_value is not None:
            # Note(rocha): protocol should always be tcp as the docker
            # command client does not handle https (see bug #1604812).
            params = {
                'protocol': 'tcp',
                'address': output_value,
                'port': DOCKER_PORT,
            }
            value = "%(protocol)s://%(address)s:%(port)s" % params
            setattr(cluster, self.cluster_attr, value)


class ServerAddressOutputMapping(template_def.NodeGroupOutputMapping):
    public_ip_output_key = None
    private_ip_output_key = None

    def __init__(self, dummy_arg, nodegroup_attr=None, nodegroup_uuid=None):
        self.heat_output = self.public_ip_output_key
        self.nodegroup_attr = nodegroup_attr
        self.nodegroup_uuid = nodegroup_uuid
        self.is_stack_param = False


class MasterAddressOutputMapping(ServerAddressOutputMapping):
    public_ip_output_key = ['swarm_primary_master',
                            'swarm_secondary_masters']
    private_ip_output_key = ['swarm_primary_master_private',
                             'swarm_secondary_masters_private']

    def set_output(self, stack, cluster_template, cluster):
        if not cluster.floating_ip_enabled:
            self.heat_output = self.private_ip_output_key

        LOG.debug("Using heat_output: %s", self.heat_output)
        _master_addresses = []
        for output in stack.to_dict().get('outputs', []):
            if output['output_key'] in self.heat_output:
                _master_addresses += output['output_value']

        for ng in cluster.nodegroups:
            if ng.uuid == self.nodegroup_uuid:
                setattr(ng, self.nodegroup_attr, _master_addresses)


class NodeAddressOutputMapping(ServerAddressOutputMapping):
    public_ip_output_key = 'swarm_nodes'
    private_ip_output_key = 'swarm_nodes_private'

    def set_output(self, stack, cluster_template, cluster):
        if not cluster.floating_ip_enabled:
            self.heat_output = self.private_ip_output_key

        LOG.debug("Using heat_output: %s", self.heat_output)
        super(NodeAddressOutputMapping,
              self).set_output(stack, cluster_template, cluster)


class SwarmModeTemplateDefinition(template_def.BaseTemplateDefinition):
    """Docker swarm mode template."""

    def __init__(self):
        super(SwarmModeTemplateDefinition, self).__init__()
        self.add_parameter('cluster_uuid',
                           cluster_attr='uuid',
                           param_type=str)
        self.add_parameter('volume_driver',
                           cluster_template_attr='volume_driver')
        self.add_parameter('external_network',
                           cluster_template_attr='external_network_id',
                           required=True)
        self.add_parameter('fixed_network',
                           cluster_template_attr='fixed_network')
        self.add_parameter('fixed_subnet',
                           cluster_template_attr='fixed_subnet')
        self.add_parameter('tls_disabled',
                           cluster_template_attr='tls_disabled',
                           required=True)
        self.add_parameter('docker_storage_driver',
                           cluster_template_attr='docker_storage_driver')

        self.add_output('api_address',
                        cluster_attr='api_address',
                        mapping_type=SwarmModeApiAddressOutputMapping)

    def get_params(self, context, cluster_template, cluster, **kwargs):
        extra_params = kwargs.pop('extra_params', {})
        # HACK(apmelton) - This uses the user's bearer token, ideally
        # it should be replaced with an actual trust token with only
        # access to do what the template needs it to do.
        osc = self.get_osc(context)
        # NOTE: Sometimes, version discovery fails when Magnum cannot talk to
        # Keystone via specified magnum_client.endpoint_type intended for
        # cluster instances either because it is not unreachable from the
        # controller or CA certs are missing for TLS enabled interface and the
        # returned auth_url may not be suffixed with /v1 in which case append
        # the url with the suffix so that instances can still talk to Magnum.
        magnum_url = osc.magnum_url()
        extra_params['magnum_url'] = magnum_url + ('' if
                                                   magnum_url.endswith('/v1')
                                                   else '/v1')

        label_list = ['rexray_preempt', 'availability_zone']

        extra_params['auth_url'] = context.auth_url
        extra_params['nodes_affinity_policy'] = \
            CONF.cluster.nodes_affinity_policy

        labels = self._get_relevant_labels(cluster, kwargs)

        for label in label_list:
            extra_params[label] = labels.get(label)

        # set docker_volume_type
        # use the configuration default if None provided
        docker_volume_type = cluster.labels.get(
            'docker_volume_type', CONF.cinder.default_docker_volume_type)
        extra_params['docker_volume_type'] = docker_volume_type

        return super(SwarmModeTemplateDefinition,
                     self).get_params(context, cluster_template, cluster,
                                      extra_params=extra_params,
                                      **kwargs)

    def get_nodegroup_param_maps(self, master_params=None, worker_params=None):
        master_params = master_params or dict()
        worker_params = worker_params or dict()
        master_params.update({
            'master_flavor': 'flavor_id',
            'master_image': 'image_id',
            'docker_volume_size': 'docker_volume_size'
        })
        worker_params.update({
            'number_of_nodes': 'node_count',
            'node_flavor': 'flavor_id',
            'node_image': 'image_id',
            'docker_volume_size': 'docker_volume_size'
        })
        return super(
            SwarmModeTemplateDefinition, self).get_nodegroup_param_maps(
                master_params=master_params, worker_params=worker_params)

    def update_outputs(self, stack, cluster_template, cluster,
                       nodegroups=None):
        nodegroups = nodegroups or [cluster.default_ng_worker,
                                    cluster.default_ng_master]
        for nodegroup in nodegroups:
            if nodegroup.role == 'master':
                self.add_output('swarm_masters',
                                nodegroup_attr='node_addresses',
                                nodegroup_uuid=nodegroup.uuid,
                                mapping_type=MasterAddressOutputMapping)
            else:
                self.add_output('swarm_nodes',
                                nodegroup_attr='node_addresses',
                                nodegroup_uuid=nodegroup.uuid,
                                mapping_type=NodeAddressOutputMapping)
                self.add_output(
                    'number_of_nodes', nodegroup_attr='node_count',
                    nodegroup_uuid=nodegroup.uuid, is_stack_param=True,
                    mapping_type=template_def.NodeGroupOutputMapping)
        super(SwarmModeTemplateDefinition,
              self).update_outputs(stack, cluster_template, cluster,
                                   nodegroups=nodegroups)

    def get_env_files(self, cluster_template, cluster, nodegroup=None):
        env_files = []

        template_def.add_priv_net_env_file(env_files, cluster_template,
                                           cluster)
        template_def.add_volume_env_file(env_files, cluster,
                                         nodegroup=nodegroup)
        template_def.add_lb_env_file(env_files, cluster)
        template_def.add_fip_env_file(env_files, cluster)

        return env_files

    def get_scale_params(self, context, cluster, node_count,
                         scale_manager=None, nodes_to_remove=None):
        scale_params = dict()
        scale_params['number_of_nodes'] = node_count
        return scale_params
