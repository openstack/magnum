# -*- encoding: utf-8 -*-
#
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

import json

from oslo.config import cfg
from oslo.db import options as db_options
from oslo.db.sqlalchemy import models
import six.moves.urllib.parse as urlparse
from sqlalchemy import Column
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Integer
from sqlalchemy import schema
from sqlalchemy import String
from sqlalchemy.types import TypeDecorator, TEXT

from magnum.common import paths


sql_opts = [
    cfg.StrOpt('mysql_engine',
               default='InnoDB',
               help='MySQL engine to use.')
]

_DEFAULT_SQL_CONNECTION = 'sqlite:///' + paths.state_path_def('magnum.sqlite')


cfg.CONF.register_opts(sql_opts, 'database')
db_options.set_defaults(cfg.CONF, _DEFAULT_SQL_CONNECTION, 'magnum.sqlite')


def table_args():
    engine_name = urlparse.urlparse(cfg.CONF.database.connection).scheme
    if engine_name == 'mysql':
        return {'mysql_engine': cfg.CONF.database.mysql_engine,
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
            raise TypeError("%s supposes to store %s objects, but %s given"
                            % (self.__class__.__name__,
                               self.type.__name__,
                               type(value).__name__))
        serialized_value = json.dumps(value)
        return serialized_value

    def process_result_value(self, value, dialect):
        if value is not None:
            value = json.loads(value)
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

    def save(self, session=None):
        import magnum.db.sqlalchemy.api as db_api

        if session is None:
            session = db_api.get_session()

        super(MagnumBase, self).save(session)

Base = declarative_base(cls=MagnumBase)


class Bay(Base):
    """Represents a bay."""

    __tablename__ = 'bay'
    __table_args__ = (
        schema.UniqueConstraint('uuid', name='uniq_bay0uuid'),
        table_args()
        )
    id = Column(Integer, primary_key=True)
    uuid = Column(String(36))
    name = Column(String(255))
    baymodel_id = Column(String(255))
    node_count = Column(Integer())


class BayModel(Base):
    """Represents a bay model."""

    __tablename__ = 'baymodel'
    __table_args__ = (
        schema.UniqueConstraint('uuid', name='uniq_baymodel0uuid'),
        table_args()
        )
    id = Column(Integer, primary_key=True)
    uuid = Column(String(36))
    name = Column(String(255))
    image_id = Column(String(255))
    flavor_id = Column(String(255))
    keypair_id = Column(String(255))
    external_network_id = Column(String(255))
    dns_nameserver = Column(String(255))


class Container(Base):
    """Represents a container."""

    __tablename__ = 'container'
    __table_args__ = (
        schema.UniqueConstraint('uuid', name='uniq_container0uuid'),
        table_args()
        )
    id = Column(Integer, primary_key=True)
    uuid = Column(String(36))
    name = Column(String(255))
    image_id = Column(String(255))


class Node(Base):
    """Represents a node."""

    __tablename__ = 'node'
    __table_args__ = (
        schema.UniqueConstraint('uuid', name='uniq_node0uuid'),
        table_args()
        )
    id = Column(Integer, primary_key=True)
    uuid = Column(String(36))
    type = Column(String(20))
    image_id = Column(String(255))
    ironic_node_id = Column(String(36))


class Pod(Base):
    """Represents a pod."""

    __tablename__ = 'pod'
    __table_args__ = (
        schema.UniqueConstraint('uuid', name='uniq_pod0uuid'),
        table_args()
        )
    id = Column(Integer, primary_key=True)
    uuid = Column(String(36))
    name = Column(String(255))
    desc = Column(String(255))
    bay_uuid = Column(String(36))
    images = Column(JSONEncodedList)
    labels = Column(JSONEncodedDict)
    status = Column(String(255))


class Service(Base):
    """Represents a software service."""

    __tablename__ = 'service'
    __table_args__ = (
        schema.UniqueConstraint('uuid', name='uniq_service0uuid'),
        table_args()
        )
    id = Column(Integer, primary_key=True)
    uuid = Column(String(36))
    name = Column(String(255))
    bay_uuid = Column(String(36))
    labels = Column(JSONEncodedDict)
    selector = Column(JSONEncodedDict)
    ip = Column(String(36))
    port = Column(Integer())


class ReplicationController(Base):
    """Represents a pod replication controller."""

    __tablename__ = 'replicationcontroller'
    __table_args__ = (
        schema.UniqueConstraint('uuid',
                                name='uniq_replicationcontroller0uuid'),
        table_args()
        )
    id = Column(Integer, primary_key=True)
    uuid = Column(String(36))
    name = Column(String(255))
    bay_uuid = Column(String(36))
    images = Column(JSONEncodedList)
    selector = Column(JSONEncodedDict)
    replicas = Column(Integer())
