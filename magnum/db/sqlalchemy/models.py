# Copyright 2013 Hewlett-Packard Development Company, L.P.
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

"""
SQLAlchemy models for container service
"""
from urllib import parse as urlparse

from oslo_db.sqlalchemy import models
from oslo_serialization import jsonutils
from sqlalchemy import Boolean
from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import Integer
from sqlalchemy.orm import declarative_base
from sqlalchemy import schema
from sqlalchemy import Text
from sqlalchemy.types import TypeDecorator, TEXT, String

import magnum.conf

CONF = magnum.conf.CONF


def table_args():
    engine_name = urlparse.urlparse(CONF.database.connection).scheme
    if engine_name == 'mysql':
        return {'mysql_engine': CONF.database.mysql_engine,
                'mysql_charset': "utf8"}
    return None


class JsonEncodedType(TypeDecorator):
    """Abstract base type serialized as json-encoded string in db."""
    type = None
    impl = TEXT

    def process_bind_param(self, value, dialect):
        if value is None:
            # Save default value according to current type to keep the
            # interface the consistent.
            value = self.type()
        elif not isinstance(value, self.type):
            raise TypeError("%(class)s supposes to store "
                            "%(type)s objects, but %(value)s "
                            "given" % {'class': self.__class__.__name__,
                                       'type': self.type.__name__,
                                       'value': type(value).__name__})
        serialized_value = jsonutils.dumps(value)
        return serialized_value

    def process_result_value(self, value, dialect):
        if value is not None:
            value = jsonutils.loads(value)
        return value


class JSONEncodedDict(JsonEncodedType):
    """Represents dict serialized as json-encoded string in db."""
    type = dict


class JSONEncodedList(JsonEncodedType):
    """Represents list serialized as json-encoded string in db."""
    type = list


class MagnumBase(models.TimestampMixin,
                 models.ModelBase):

    metadata = None

    def as_dict(self):
        d = {}
        for c in self.__table__.columns:
            d[c.name] = self[c.name]
        return d


Base = declarative_base(cls=MagnumBase)


class Cluster(Base):
    """Represents a Cluster."""

    __tablename__ = 'cluster'
    __table_args__ = (
        schema.UniqueConstraint('uuid'),
        table_args()
    )
    id = Column(Integer, primary_key=True)
    project_id = Column(String(255))
    user_id = Column(String(255))
    uuid = Column(String(36))
    name = Column(String(255))
    cluster_template_id = Column(String(255))
    keypair = Column(String(255))
    docker_volume_size = Column(Integer())
    labels = Column(JSONEncodedDict)
    master_flavor_id = Column(String(255))
    flavor_id = Column(String(255))
    stack_id = Column(String(255))
    api_address = Column(String(255))
    status = Column(String(20))
    status_reason = Column(Text)
    health_status = Column(String(20))
    health_status_reason = Column(JSONEncodedDict)
    create_timeout = Column(Integer())
    discovery_url = Column(String(255))
    # TODO(wanghua): encrypt trust_id in db
    trust_id = Column(String(255))
    trustee_username = Column(String(255))
    trustee_user_id = Column(String(255))
    # TODO(wanghua): encrypt trustee_password in db
    trustee_password = Column(String(255))
    coe_version = Column(String(255))
    container_version = Column(String(255))
    # (yuanying) if we use barbican,
    # cert_ref size is determined by below format
    # * http(s)://${DOMAIN_NAME}/v1/containers/${UUID}
    # as a result, cert_ref length is estimated to 312 chars.
    # but we can use another backend to store certs.
    # so, we use 512 chars to get some buffer.
    ca_cert_ref = Column(String(512))
    magnum_cert_ref = Column(String(512))
    etcd_ca_cert_ref = Column(String(512))
    front_proxy_ca_cert_ref = Column(String(512))
    fixed_network = Column(String(255))
    fixed_subnet = Column(String(255))
    floating_ip_enabled = Column(Boolean, default=True)
    master_lb_enabled = Column(Boolean, default=False)


class ClusterTemplate(Base):
    """Represents a ClusterTemplate."""

    __tablename__ = 'cluster_template'
    __table_args__ = (
        schema.UniqueConstraint('uuid'),
        table_args()
    )
    id = Column(Integer, primary_key=True)
    uuid = Column(String(36))
    project_id = Column(String(255))
    user_id = Column(String(255))
    name = Column(String(255))
    image_id = Column(String(255))
    flavor_id = Column(String(255))
    master_flavor_id = Column(String(255))
    keypair_id = Column(String(255))
    external_network_id = Column(String(255))
    fixed_network = Column(String(255))
    fixed_subnet = Column(String(255))
    network_driver = Column(String(255))
    volume_driver = Column(String(255))
    dns_nameserver = Column(String(255))
    apiserver_port = Column(Integer())
    docker_volume_size = Column(Integer())
    docker_storage_driver = Column(String(255))
    cluster_distro = Column(String(255))
    coe = Column(String(255))
    http_proxy = Column(String(255))
    https_proxy = Column(String(255))
    no_proxy = Column(String(255))
    registry_enabled = Column(Boolean, default=False)
    labels = Column(JSONEncodedDict)
    tls_disabled = Column(Boolean, default=False)
    public = Column(Boolean, default=False)
    server_type = Column(String(255))
    insecure_registry = Column(String(255))
    master_lb_enabled = Column(Boolean, default=False)
    floating_ip_enabled = Column(Boolean, default=True)
    hidden = Column(Boolean, default=False)
    tags = Column(String(255))
    driver = Column(String(255))


class X509KeyPair(Base):
    """X509KeyPair"""
    __tablename__ = 'x509keypair'
    __table_args__ = (
        schema.UniqueConstraint('uuid',
                                name='uniq_x509keypair0uuid'),
        table_args()
    )
    id = Column(Integer, primary_key=True)
    uuid = Column(String(36))
    certificate = Column(Text())
    private_key = Column(Text())
    private_key_passphrase = Column(Text())
    intermediates = Column(Text())
    project_id = Column(String(255))
    user_id = Column(String(255))


class MagnumService(Base):
    """Represents health status of various magnum services"""
    __tablename__ = 'magnum_service'
    __table_args__ = (
        schema.UniqueConstraint("host", "binary",
                                name="uniq_magnum_service0host0binary"),
        table_args()
    )

    id = Column(Integer, primary_key=True)
    host = Column(String(255))
    binary = Column(String(255))
    disabled = Column(Boolean, default=False)
    disabled_reason = Column(String(255))
    last_seen_up = Column(DateTime, nullable=True)
    forced_down = Column(Boolean, default=False)
    report_count = Column(Integer, nullable=False, default=0)


class Quota(Base):
    """Represents Quota for a resource within a project"""
    __tablename__ = 'quotas'
    __table_args__ = (
        schema.UniqueConstraint(
            "project_id", "resource",
            name='uniq_quotas0project_id0resource'),
        table_args()
    )
    id = Column(Integer, primary_key=True)
    project_id = Column(String(255))
    resource = Column(String(255))
    hard_limit = Column(Integer())


class Federation(Base):
    """Represents a Federation."""
    __tablename__ = 'federation'
    __table_args__ = (
        schema.UniqueConstraint("uuid", name="uniq_federation0uuid"),
        table_args()
    )
    id = Column(Integer, primary_key=True)
    project_id = Column(String(255))
    uuid = Column(String(36))
    name = Column(String(255))
    hostcluster_id = Column(String(255))
    member_ids = Column(JSONEncodedList)
    status = Column(String(20))
    status_reason = Column(Text)
    properties = Column(JSONEncodedDict)


class NodeGroup(Base):
    """Represents a NodeGroup."""

    __tablename__ = 'nodegroup'
    __table_args__ = (
        schema.UniqueConstraint('uuid', name='uniq_nodegroup0uuid'),
        schema.UniqueConstraint(
            'cluster_id', 'name',
            name='uniq_nodegroup0cluster_id0name'),
        table_args()
    )
    id = Column(Integer, primary_key=True)
    uuid = Column(String(36))
    name = Column(String(255))
    cluster_id = Column(String(255))
    project_id = Column(String(255))
    docker_volume_size = Column(Integer(), nullable=True)
    labels = Column(JSONEncodedDict, nullable=True)
    flavor_id = Column(String(255), nullable=True)
    image_id = Column(String(255), nullable=True)
    node_addresses = Column(JSONEncodedList, nullable=True)
    node_count = Column(Integer())
    role = Column(String(255))
    # NOTE(ttsiouts) We have to define the min and
    # max number of nodes for each nodegroup
    max_node_count = Column(Integer())
    min_node_count = Column(Integer())
    is_default = Column(Boolean, default=False)
    stack_id = Column(String(255))
    status = Column(String(20))
    status_reason = Column(Text)
    version = Column(String(20))
