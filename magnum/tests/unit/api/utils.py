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
from magnum.api.controllers.v1 import pod as pod_controller
from magnum.api.controllers.v1 import replicationcontroller as rc_controller
from magnum.api.controllers.v1 import service as service_controller
from magnum.api.controllers.v1 import x509keypair as x509keypair_controller
from magnum.tests.unit.db import utils


def remove_internal(values, internal):
    # NOTE(yuriyz): internal attributes should not be posted, except uuid
    int_attr = [attr.lstrip('/') for attr in internal if attr != '/uuid']
    return {k: v for (k, v) in values.items() if k not in int_attr}


def baymodel_post_data(**kw):
    baymodel = utils.get_test_baymodel(**kw)
    internal = baymodel_controller.BayModelPatchType.internal_attrs()
    return remove_internal(baymodel, internal)


def bay_post_data(**kw):
    bay = utils.get_test_bay(**kw)
    bay['bay_create_timeout'] = kw.get('bay_create_timeout', 15)
    internal = bay_controller.BayPatchType.internal_attrs()
    return remove_internal(bay, internal)


def cert_post_data(**kw):
    return {
        'bay_uuid': kw.get('bay_uuid', '5d12f6fd-a196-4bf0-ae4c-1f639a523a52'),
        'csr': kw.get('csr', 'fake-csr'),
        'pem': kw.get('pem', 'fake-pem')
    }


def pod_post_data(**kw):
    pod = utils.get_test_pod(**kw)
    if 'manifest' not in pod:
        pod['manifest'] = '''{
            "metadata": {
                "name": "name_of_pod"
            },
            "spec": {
                "containers": [
                    {
                        "name": "test",
                        "image": "test"
                    }
                ]
            }
        }'''
    internal = pod_controller.PodPatchType.internal_attrs()
    return remove_internal(pod, internal)


def service_post_data(**kw):
    service = utils.get_test_service(**kw)
    if 'manifest' not in service:
        service['manifest'] = '''{
            "metadata": {
                "name": "test",
                "labels": {
                    "key": "value"
                }
            },
            "spec": {
                "ports": [
                    {
                    "port": 88,
                    "targetPort": 6379,
                    "protocol": "TCP"
                    }
                ],
                "selector": {
                    "bar": "foo"
                }
            }
            }'''
    internal = service_controller.ServicePatchType.internal_attrs()
    return remove_internal(service, internal)


def rc_post_data(**kw):
    rc = utils.get_test_rc(**kw)
    if 'manifest' not in rc:
        rc['manifest'] = '''{
            "metadata": {
                "name": "name_of_rc"
                },
                "spec":{
                    "replicas":2,
                    "selector":{
                        "name":"frontend"
                    },
                    "template":{
                        "metadata":{
                            "labels":{
                                "name":"frontend"
                            }
                        },
                        "spec":{
                            "containers":[
                                {
                                    "name":"test-redis",
                                    "image":"steak/for-dinner",
                                    "ports":[
                                        {
                                            "containerPort":80,
                                            "protocol":"TCP"
                                        }
                                    ]
                                }
                            ]
                        }
                   }
               }
           }'''
    internal = rc_controller.ReplicationControllerPatchType.internal_attrs()
    return remove_internal(rc, internal)


def x509keypair_post_data(**kw):
    x509keypair = utils.get_test_x509keypair(**kw)
    internal = x509keypair_controller.X509KeyPairPatchType.internal_attrs()
    return remove_internal(x509keypair, internal)


def mservice_get_data(**kw):
    """Simulate what the RPC layer will get from DB """
    faketime = datetime.datetime(2001, 1, 1, tzinfo=pytz.UTC)
    return {
        'binary': kw.get('binary', 'fake-binary'),
        'host': kw.get('host', 'fake-host'),
        'id': kw.get('id', '13'),
        'report_count': kw.get('report_count', '13'),
        'disabled': kw.get('disabled', False),
        'disabled_reason': kw.get('disabled_reason', None),
        'forced_down': kw.get('forced_down', False),
        'last_seen_at': kw.get('last_seen_at', faketime),
        'created_at': kw.get('created_at', faketime),
        'updated_at': kw.get('updated_at', faketime),
    }
