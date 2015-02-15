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

from magnum.api.controllers.v1 import bay as bay_controller
from magnum.api.controllers.v1 import baymodel as baymodel_controller
from magnum.api.controllers.v1 import node as node_controller
from magnum.api.controllers.v1 import pod as pod_controller
from magnum.api.controllers.v1 import replicationcontroller as rc_controller
from magnum.api.controllers.v1 import service as service_controller
from magnum.tests.db import utils


def remove_internal(values, internal):
    # NOTE(yuriyz): internal attributes should not be posted, except uuid
    int_attr = [attr.lstrip('/') for attr in internal if attr != '/uuid']
    return dict([(k, v) for (k, v) in values.iteritems() if k not in int_attr])


def baymodel_post_data(**kw):
    baymodel = utils.get_test_baymodel(**kw)
    internal = baymodel_controller.BayModelPatchType.internal_attrs()
    return remove_internal(baymodel, internal)


def bay_post_data(**kw):
    bay = utils.get_test_bay(**kw)
    internal = bay_controller.BayPatchType.internal_attrs()
    return remove_internal(bay, internal)


def pod_post_data(**kw):
    pod = utils.get_test_pod(**kw)
    if 'manifest' not in pod:
        pod['manifest'] = '''{
            "id": "name_of_pod",
            "labels": {
                "foo": "foo1"
            }
        }'''
    internal = pod_controller.PodPatchType.internal_attrs()
    return remove_internal(pod, internal)


def service_post_data(**kw):
    service = utils.get_test_service(**kw)
    if 'manifest' not in service:
        service['manifest'] = '''{
            "id": "service_foo",
            "kind": "Service",
            "apiVersion": "v1beta1",
            "port": 88,
            "selector": {
                "bar": "foo"
            },
            "labels": {
                "bar": "foo"
            }
        }'''
    internal = service_controller.ServicePatchType.internal_attrs()
    return remove_internal(service, internal)


def rc_post_data(**kw):
    rc = utils.get_test_rc(**kw)
    if 'manifest' not in rc:
        rc['manifest'] = '''{
            "id": "name_of_rc",
            "replicas": 3,
            "labels": {
                "foo": "foo1"
            }
        }'''
    internal = rc_controller.ReplicationControllerPatchType.internal_attrs()
    return remove_internal(rc, internal)


def node_post_data(**kw):
    node = utils.get_test_node(**kw)
    internal = node_controller.NodePatchType.internal_attrs()
    return remove_internal(node, internal)
