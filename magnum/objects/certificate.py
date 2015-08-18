# coding=utf-8
#
#
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

from oslo_versionedobjects import fields

from magnum.objects import base


@base.MagnumObjectRegistry.register
class Certificate(base.MagnumPersistentObject, base.MagnumObject,
                  base.MagnumObjectDictCompat):
    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'project_id': fields.StringField(nullable=True),
        'user_id': fields.StringField(nullable=True),
        'bay_uuid': fields.StringField(nullable=True),
        'csr': fields.StringField(nullable=True),
        'pem': fields.StringField(nullable=True),
    }

    @classmethod
    def from_object_bay(cls, bay):
        return cls(project_id=bay.project_id,
                   user_id=bay.user_id,
                   bay_uuid=bay.uuid)

    @classmethod
    def from_db_bay(cls, bay):
        return cls(project_id=bay['project_id'],
                   user_id=bay['user_id'],
                   bay_uuid=bay['uuid'])
