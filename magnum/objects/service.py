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

import ast

from oslo_versionedobjects import fields

from magnum.common import exception
from magnum.common.pythonk8sclient.swagger_client import rest
from magnum.db import api as dbapi
from magnum.objects import base
from magnum.objects import fields as magnum_fields


@base.MagnumObjectRegistry.register
class Service(base.MagnumPersistentObject, base.MagnumObject,
              base.MagnumObjectDictCompat):
    # Version 1.0: Initial version
    VERSION = '1.0'

    dbapi = dbapi.get_instance()

    fields = {
        'id': fields.IntegerField(),
        'uuid': fields.StringField(nullable=True),
        'name': fields.StringField(nullable=True),
        'project_id': fields.StringField(nullable=True),
        'user_id': fields.StringField(nullable=True),
        'bay_uuid': fields.StringField(nullable=True),
        'labels': fields.DictOfStringsField(nullable=True),
        'selector': fields.DictOfStringsField(nullable=True),
        'ip': fields.StringField(nullable=True),
        'ports': magnum_fields.ListOfDictsField(nullable=True),
        'manifest_url': fields.StringField(nullable=True),
        'manifest': fields.StringField(nullable=True),
    }

    @base.remotable_classmethod
    def get_by_uuid(cls, context, uuid, bay_uuid, k8s_api):
        """Find a service based on service uuid and UUID of the Bay

        :param context: Security context
        :param uuid: the uuid of a service.
        :param bay_uuid: the UUID of the Bay
        :param k8s_api: k8s API object

        :returns: a :class:`Service` object.
        """
        try:
            resp = k8s_api.list_namespaced_service(namespace='default')
        except rest.ApiException as err:
            raise exception.KubernetesAPIFailed(err=err)

        if resp is None:
            raise exception.ServiceListNotFound(bay_uuid=bay_uuid)

        service = {}
        for service_entry in resp.items:
            if service_entry.metadata.uid == uuid:
                service['uuid'] = service_entry.metadata.uid
                service['name'] = service_entry.metadata.name
                service['project_id'] = context.project_id
                service['user_id'] = context.user_id
                service['bay_uuid'] = bay_uuid
                service['labels'] = ast.literal_eval(
                    service_entry.metadata.labels)
                if not service_entry.spec.selector:
                    service['selector'] = {}
                else:
                    service['selector'] = ast.literal_eval(
                        service_entry.spec.selector)
                service['ip'] = service_entry.spec.cluster_ip
                service_value = []
                for p in service_entry.spec.ports:
                    ports = p.to_dict()
                    if not ports['name']:
                        ports['name'] = 'k8s-service'
                    service_value.append(ports)

                service['ports'] = service_value

                service_obj = Service(context, **service)
                return service_obj
        raise exception.ServiceNotFound(service=uuid)

    @base.remotable_classmethod
    def get_by_name(cls, context, name, bay_uuid, k8s_api):
        """Find a service based on service name and UUID of the Bay

        :param context: Security context
        :param name: the name of a service.
        :param bay_uuid: the UUID of the Bay
        :param k8s_api: k8s API object

        :returns: a :class:`Service` object.
        """
        try:
            resp = k8s_api.read_namespaced_service(name=name,
                                                   namespace='default')
        except rest.ApiException as err:
            raise exception.KubernetesAPIFailed(err=err)

        if resp is None:
            raise exception.ServiceNotFound(service=name)

        service = {}
        service['uuid'] = resp.metadata.uid
        service['name'] = resp.metadata.name
        service['project_id'] = context.project_id
        service['user_id'] = context.user_id
        service['bay_uuid'] = bay_uuid
        service['labels'] = ast.literal_eval(resp.metadata.labels)
        if not resp.spec.selector:
            service['selector'] = {}
        else:
            service['selector'] = ast.literal_eval(resp.spec.selector)
        service['ip'] = resp.spec.cluster_ip
        service_value = []
        for p in resp.spec.ports:
            ports = p.to_dict()
            if not ports['name']:
                ports['name'] = 'k8s-service'
            service_value.append(ports)

        service['ports'] = service_value

        service_obj = Service(context, **service)
        return service_obj
