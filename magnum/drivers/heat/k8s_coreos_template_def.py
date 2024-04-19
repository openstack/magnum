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

import base64
from oslo_log import log as logging
from oslo_utils import strutils

from magnum.common import utils
from magnum.common.x509 import operations as x509
from magnum.conductor.handlers.common import cert_manager
from magnum.drivers.heat import k8s_template_def
from magnum.drivers.heat import template_def
from oslo_config import cfg

CONF = cfg.CONF

LOG = logging.getLogger(__name__)


class CoreOSK8sTemplateDefinition(k8s_template_def.K8sTemplateDefinition):
    """Kubernetes template for a CoreOS."""

    def __init__(self):
        super(CoreOSK8sTemplateDefinition, self).__init__()
        self.add_parameter('docker_storage_driver',
                           cluster_template_attr='docker_storage_driver')

    def get_params(self, context, cluster_template, cluster, **kwargs):
        extra_params = kwargs.pop('extra_params', {})

        extra_params['username'] = context.user_name
        osc = self.get_osc(context)
        extra_params['region_name'] = osc.cinder_region_name()

        # set docker_volume_type
        # use the configuration default if None provided
        docker_volume_type = cluster.labels.get(
            'docker_volume_type', CONF.cinder.default_docker_volume_type)
        extra_params['docker_volume_type'] = docker_volume_type

        extra_params['nodes_affinity_policy'] = \
            CONF.cluster.nodes_affinity_policy

        if cluster_template.network_driver == 'flannel':
            extra_params["pods_network_cidr"] = \
                cluster.labels.get('flannel_network_cidr', '10.100.0.0/16')
        if cluster_template.network_driver == 'calico':
            extra_params["pods_network_cidr"] = \
                cluster.labels.get('calico_ipv4pool', '10.100.0.0/16')

        label_list = ['coredns_tag',
                      'kube_tag', 'container_infra_prefix',
                      'availability_zone',
                      'calico_tag',
                      'calico_ipv4pool',
                      'calico_ipv4pool_ipip',
                      'etcd_tag', 'flannel_tag']

        labels = self._get_relevant_labels(cluster, kwargs)

        for label in label_list:
            label_value = labels.get(label)
            if label_value:
                extra_params[label] = label_value

        cert_manager_api = cluster.labels.get('cert_manager_api')
        if strutils.bool_from_string(cert_manager_api):
            extra_params['cert_manager_api'] = cert_manager_api
            ca_cert = cert_manager.get_cluster_ca_certificate(cluster)
            extra_params['ca_key'] = x509.decrypt_key(
                ca_cert.get_private_key(),
                ca_cert.get_private_key_passphrase()).replace("\n", "\\n")

        plain_openstack_ca = utils.get_openstack_ca()
        encoded_openstack_ca = base64.b64encode(plain_openstack_ca.encode())
        extra_params['openstack_ca_coreos'] = encoded_openstack_ca.decode()

        return super(CoreOSK8sTemplateDefinition,
                     self).get_params(context, cluster_template, cluster,
                                      extra_params=extra_params,
                                      **kwargs)

    def get_env_files(self, cluster_template, cluster, nodegroup=None):
        env_files = []

        template_def.add_priv_net_env_file(env_files, cluster_template,
                                           cluster)
        template_def.add_etcd_volume_env_file(env_files, cluster)
        template_def.add_volume_env_file(env_files, cluster,
                                         nodegroup=nodegroup)
        template_def.add_lb_env_file(env_files, cluster)
        template_def.add_fip_env_file(env_files, cluster)

        return env_files
