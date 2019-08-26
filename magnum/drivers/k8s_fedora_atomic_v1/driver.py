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

from oslo_log import log as logging
from pbr.version import SemanticVersion as SV

from magnum.common import clients
from magnum.common import exception
from magnum.drivers.heat import driver
from magnum.drivers.k8s_fedora_atomic_v1 import template_def

LOG = logging.getLogger(__name__)


class Driver(driver.KubernetesDriver):

    @property
    def provides(self):
        return [
            {'server_type': 'vm',
             'os': 'fedora-atomic',
             'coe': 'kubernetes'},
        ]

    def get_template_definition(self):
        return template_def.AtomicK8sTemplateDefinition()

    def upgrade_cluster(self, context, cluster, cluster_template,
                        max_batch_size, nodegroup, scale_manager=None,
                        rollback=False):
        osc = clients.OpenStackClients(context)
        _, heat_params, _ = (
            self._extract_template_definition(context, cluster,
                                              scale_manager=scale_manager))
        # Extract labels/tags from cluster not template
        # There are some version tags are not decalared in labels explicitly,
        # so we need to get them from heat_params based on the labels given in
        # new cluster template.
        current_addons = {}
        new_addons = {}
        for label in cluster_template.labels:
            # This is upgrade API, so we don't introduce new stuff by this API,
            # but just focus on the version change.
            new_addons[label] = cluster_template.labels[label]
            if ((label.endswith('_tag') or
                 label.endswith('_version')) and label in heat_params):
                current_addons[label] = heat_params[label]
                try:
                    if (SV.from_pip_string(new_addons[label]) <
                            SV.from_pip_string(current_addons[label])):
                        raise exception.InvalidVersion(tag=label)
                except Exception as e:
                    # NOTE(flwang): Different cloud providers may use different
                    # tag/version format which maybe not able to parse by
                    # SemanticVersion. For this case, let's just skip it.
                    LOG.debug("Failed to parse tag/version %s", str(e))

        heat_params["server_image"] = cluster_template.image_id
        heat_params["master_image"] = cluster_template.image_id
        heat_params["minion_image"] = cluster_template.image_id
        # NOTE(flwang): Overwrite the kube_tag as well to avoid a server
        # rebuild then do the k8s upgrade again, when both image id and
        # kube_tag changed
        heat_params["kube_tag"] = cluster_template.labels["kube_tag"]
        heat_params["kube_version"] = cluster_template.labels["kube_tag"]
        heat_params["master_kube_tag"] = cluster_template.labels["kube_tag"]
        heat_params["minion_kube_tag"] = cluster_template.labels["kube_tag"]
        heat_params["update_max_batch_size"] = max_batch_size
        # Rules: 1. No downgrade 2. Explicitly override 3. Merging based on set
        # Update heat_params based on the data generated above
        del heat_params['kube_service_account_private_key']
        del heat_params['kube_service_account_key']

        for label in new_addons:
            heat_params[label] = cluster_template.labels[label]

        cluster['cluster_template_id'] = cluster_template.uuid
        new_labels = cluster.labels.copy()
        new_labels.update(cluster_template.labels)
        cluster['labels'] = new_labels

        fields = {
            'existing': True,
            'parameters': heat_params,
            'disable_rollback': not rollback
        }
        osc.heat().stacks.update(cluster.stack_id, **fields)
