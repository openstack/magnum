# Copyright 2013 - Red Hat, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
SQLAlchemy models for application data.
"""

import json

from oslo.config import cfg
from oslo.db import exception as db_exc
from oslo.db.sqlalchemy import models
import six
from six import moves
from sqlalchemy.ext import declarative
from sqlalchemy.orm import exc
from sqlalchemy import types

from magnum.common import exception
from magnum import objects
from magnum.objects import sqlalchemy as object_sqla


def table_args():
    cfg.CONF.import_opt('connection', 'oslo.db.options',
                        group='database')
    if cfg.CONF.database.connection is None:
        # this is only within some object tests where
        # the object classes are directly imported.
        return None
    engine_name = moves.urllib.parse.urlparse(
        cfg.CONF.database.connection).scheme
    if engine_name == 'mysql':
        return {'mysql_engine': 'InnoDB',
                'mysql_charset': "utf8"}
    return None


def model_query(context, model, *args, **kwargs):
    """Query helper.

    :param context: context to query under
    :param session: if present, the session to use
    """

    session = kwargs.get('session') or object_sqla.get_session()

    query = session.query(model, *args)
    return query


class MagnumBase(models.TimestampMixin, models.ModelBase):

    metadata = None

    @classmethod
    def obj_name(cls):
        return cls.__name__

    def as_dict(self):
        d = {}
        for c in self.__table__.columns:
            d[c.name] = self[c.name]
        for k in self._extra_keys:
            d[k] = self[k]
        return d

    @classmethod
    def get_session(cls):
        return object_sqla.get_session()

    @classmethod
    def get_by_id(cls, context, item_id):
        try:
            session = MagnumBase.get_session()
            return session.query(cls).filter_by(id=item_id).one()
        except exc.NoResultFound:
            cls._raise_not_found(item_id)

    @classmethod
    def get_by_uuid(cls, context, item_uuid):
        try:
            session = MagnumBase.get_session()
            return session.query(cls).filter_by(uuid=item_uuid).one()
        except exc.NoResultFound:
            cls._raise_not_found(item_uuid)

    @classmethod
    def _raise_duplicate_object(cls):
        if hasattr(cls, '__resource__'):
            raise exception.ResourceExists(name=cls.__resource__)
        else:
            raise exception.ObjectNotUnique(name=cls.__tablename__)

    def _non_updatable_fields(self):
        return set(('uuid', 'id'))

    def _lazyhasattr(self, name):
        return any(name in d for d in (self.__dict__,
                                       self.__class__.__dict__))

    def update(self, data):
        for field in set(six.iterkeys(data)) - self._non_updatable_fields():
            if self._lazyhasattr(field):
                setattr(self, field, data[field])

    def save(self, context):
        if objects.transition_schema():
            self.add_forward_schema_changes()

        session = MagnumBase.get_session()
        with session.begin():
            session.merge(self)

    def create(self, context):
        session = MagnumBase.get_session()
        try:
            with session.begin():
                session.add(self)
        except (db_exc.DBDuplicateEntry):
            self.__class__._raise_duplicate_object()

    def destroy(self, context):
        session = MagnumBase.get_session()
        with session.begin():
            session.query(self.__class__).filter_by(
                id=self.id).delete()

    @classmethod
    def _raise_not_found(cls, item_id):
        """Raise a not found exception."""
        if hasattr(cls, '__resource__'):
            raise exception.ResourceNotFound(name=cls.__resource__, id=item_id)
        else:
            raise exception.ObjectNotFound(name=cls.__tablename__, id=item_id)


Base = declarative.declarative_base(cls=MagnumBase)


class JsonEncodedType(types.TypeDecorator):
    """Abstract base type serialized as json-encoded string in db."""
    type = None
    impl = types.TEXT

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
