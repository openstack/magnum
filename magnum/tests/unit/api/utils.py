#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
"""
Utils for testing the API service.
"""
import datetime

import pytz

from magnum.api.controllers.v1 import bay as bay_controller
from magnum.api.controllers.v1 import baymodel as baymodel_controller
from magnum.api.controllers.v1 import cluster as cluster_controller
from magnum.api.controllers.v1 import cluster_template as cluster_tmp_ctrl
from magnum.api.controllers.v1 import federation as federation_controller
from magnum.tests.unit.db import utils


def remove_internal(values, internal):
    # NOTE(yuriyz): internal attributes should not be posted, except uuid
    int_attr = [attr.lstrip('/') for attr in internal if attr != '/uuid']
    return {k: v for (k, v) in values.items() if k not in int_attr}


def baymodel_post_data(**kw):
    baymodel = utils.get_test_cluster_template(**kw)
    internal = baymodel_controller.BayModelPatchType.internal_attrs()
    return remove_internal(baymodel, internal)


def cluster_template_post_data(**kw):
    cluster_template = utils.get_test_cluster_template(**kw)
    internal = cluster_tmp_ctrl.ClusterTemplatePatchType.internal_attrs()
    return remove_internal(cluster_template, internal)


def bay_post_data(**kw):
    kw.update({'for_api_use': True})
    bay = utils.get_test_cluster(**kw)
    bay['baymodel_id'] = kw.get('baymodel_id', bay['cluster_template_id'])
    bay['bay_create_timeout'] = kw.get('bay_create_timeout', 15)
    del bay['cluster_template_id']
    del bay['create_timeout']
    internal = bay_controller.BayPatchType.internal_attrs()
    return remove_internal(bay, internal)


def cluster_post_data(**kw):
    kw.update({'for_api_use': True})
    cluster = utils.get_test_cluster(**kw)
    cluster['create_timeout'] = kw.get('create_timeout', 15)
    cluster['merge_labels'] = kw.get('merge_labels', False)
    internal = cluster_controller.ClusterPatchType.internal_attrs()
    return remove_internal(cluster, internal)


def cert_post_data(**kw):
    return {
        'cluster_uuid': kw.get('cluster_uuid',
                               '5d12f6fd-a196-4bf0-ae4c-1f639a523a52'),
        'csr': kw.get('csr', 'fake-csr'),
        'pem': kw.get('pem', 'fake-pem')
    }


def quota_post_data(**kw):
    return utils.get_test_quota(**kw)


def mservice_get_data(**kw):
    """Simulate what the RPC layer will get from DB """
    faketime = datetime.datetime(2001, 1, 1, tzinfo=pytz.UTC)
    return {
        'binary': kw.get('binary', 'magnum-conductor'),
        'host': kw.get('host', 'fake-host'),
        'id': kw.get('id', 13),
        'report_count': kw.get('report_count', 13),
        'disabled': kw.get('disabled', False),
        'disabled_reason': kw.get('disabled_reason', None),
        'forced_down': kw.get('forced_down', False),
        'last_seen_at': kw.get('last_seen_at', faketime),
        'created_at': kw.get('created_at', faketime),
        'updated_at': kw.get('updated_at', faketime),
    }


def federation_post_data(**kw):
    federation = utils.get_test_federation(**kw)
    internal = federation_controller.FederationPatchType.internal_attrs()
    return remove_internal(federation, internal)


def nodegroup_post_data(**kw):
    internal = ['/cluster_id', '/project_id', '/node_addresses', '/is_default',
                '/created_at', '/updated_at', '/status', '/status_reason',
                '/version', '/stack_id']
    nodegroup = utils.get_test_nodegroup(**kw)
    nodegroup['merge_labels'] = kw.get('merge_labels', False)
    return remove_internal(nodegroup, internal)
