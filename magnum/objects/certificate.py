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
class Certificate(base.MagnumPersistentObject, base.MagnumObject):
    # Version 1.0: Initial version
    # Version 1.1: Rename bay_uuid to cluster_uuid
    # Version 1.2: Add ca_cert_type to indicate what's the CA cert type the
    #              CSR being signed

    VERSION = '1.2'

    fields = {
        'project_id': fields.StringField(nullable=True),
        'user_id': fields.StringField(nullable=True),
        'cluster_uuid': fields.StringField(nullable=True),
        'csr': fields.StringField(nullable=True),
        'pem': fields.StringField(nullable=True),
        'ca_cert_type': fields.StringField(nullable=True),
    }

    @classmethod
    def from_object_cluster(cls, cluster):
        return cls(project_id=cluster.project_id,
                   user_id=cluster.user_id,
                   cluster_uuid=cluster.uuid)

    @classmethod
    def from_db_cluster(cls, cluster):
        return cls(project_id=cluster['project_id'],
                   user_id=cluster['user_id'],
                   cluster_uuid=cluster['uuid'])
