# Copyright 2013 - Red Hat, Inc.
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

import string

import wsme
from wsme import types as wtypes

from magnum.api.controllers import common_types
from magnum.openstack.common._i18n import _


class Base(wtypes.Base):
    """Base class for all API types."""

    uri = common_types.Uri
    "URI to the resource."

    uuid = wtypes.text
    "Unique Identifier of the resource"

    def get_name(self):
        return self.__name

    def set_name(self, value):
        allowed_chars = string.letters + string.digits + '-_'
        for ch in value:
            if ch not in allowed_chars:
                raise ValueError(_('Names must only contain a-z,A-Z,0-9,-,_'))
        self.__name = value

    name = wtypes.wsproperty(str, get_name, set_name, mandatory=True)
    "Name of the resource."

    type = wtypes.text
    "The resource type."

    description = wtypes.text
    "Textual description of the resource."

    tags = [wtypes.text]
    "Tags for the resource."

    project_id = wtypes.text
    "The project that this resource belongs in."

    user_id = wtypes.text
    "The user that owns this resource."

    def __init__(self, **kwds):
        self.__name = wsme.Unset
        super(Base, self).__init__(**kwds)

    @classmethod
    def from_db_model(cls, m, host_url):
        json = m.as_dict()
        json['type'] = m.__tablename__
        json['uri'] = '%s/v1/%s/%s' % (host_url, m.__resource__, m.uuid)
        del json['id']
        return cls(**(json))

    def as_dict(self, db_model):
        valid_keys = (attr for attr in db_model.__dict__.keys()
                      if attr[:2] != '__' and attr != 'as_dict')
        return self.as_dict_from_keys(valid_keys)

    def as_dict_from_keys(self, keys):
        return dict((k, getattr(self, k))
                    for k in keys
                    if hasattr(self, k) and
                    getattr(self, k) != wsme.Unset)


class MultiType(wtypes.UserType):
    """A complex type that represents one or more types.

    Used for validating that a value is an instance of one of the types.

    :param *types: Variable-length list of types.
    """

    def __init__(self, *types):
        self.types = types

    def __str__(self):
        return ' | '.join(map(str, self.types))

    def validate(self, value):
        for t in self.types:
            if t is wsme.types.text and isinstance(value, wsme.types.bytes):
                value = value.decode()
            if isinstance(value, t):
                return value
        else:
            raise ValueError(
                _("Wrong type. Expected '%(type)s', got '%(value)s'")
                % {'type': self.types, 'value': type(value)})
