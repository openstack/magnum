#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

import ast
import functools
import inspect
import uuid

from oslo.utils import strutils
from oslo.utils import timeutils
from pecan import rest
import six
import wsme
from wsme import exc
from wsme import types as wtypes
import wsmeext.pecan as wsme_pecan


# NOTE(dims): We don't depend on oslo*i18n yet
_ = _LI = _LW = _LE = _LC = lambda x: x

state_kind = ["ok", "pods", "insufficient data"]
state_kind_enum = wtypes.Enum(str, *state_kind)
operation_kind = ('lt', 'le', 'eq', 'ne', 'ge', 'gt')
operation_kind_enum = wtypes.Enum(str, *operation_kind)


class _Base(wtypes.Base):

    @classmethod
    def from_db_model(cls, m):
        return cls(**(m.as_dict()))

    @classmethod
    def from_db_and_links(cls, m, links):
        return cls(links=links, **(m.as_dict()))

    def as_dict(self, db_model):
        valid_keys = inspect.getargspec(db_model.__init__)[0]
        if 'self' in valid_keys:
            valid_keys.remove('self')
        return self.as_dict_from_keys(valid_keys)

    def as_dict_from_keys(self, keys):
        return dict((k, getattr(self, k))
                    for k in keys
                    if hasattr(self, k) and
                    getattr(self, k) != wsme.Unset)


class Query(_Base):

    """Query filter."""

    # The data types supported by the query.
    _supported_types = ['integer', 'float', 'string', 'boolean']

    # Functions to convert the data field to the correct type.
    _type_converters = {'integer': int,
                        'float': float,
                        'boolean': functools.partial(
                            strutils.bool_from_string, strict=True),
                        'string': six.text_type,
                        'datetime': timeutils.parse_isotime}

    _op = None  # provide a default

    def get_op(self):
        return self._op or 'eq'

    def set_op(self, value):
        self._op = value

    field = wtypes.text
    "The name of the field to test"

    # op = wsme.wsattr(operation_kind, default='eq')
    # this ^ doesn't seem to work.
    op = wsme.wsproperty(operation_kind_enum, get_op, set_op)
    "The comparison operator. Defaults to 'eq'."

    value = wtypes.text
    "The value to compare against the stored data"

    type = wtypes.text
    "The data type of value to compare against the stored data"

    def __repr__(self):
        # for logging calls
        return '<Query %r %s %r %s>' % (self.field,
                                        self.op,
                                        self.value,
                                        self.type)

    @classmethod
    def sample(cls):
        return cls(field='resource_id',
                   op='eq',
                   value='bd9431c1-8d69-4ad3-803a-8d4a6b89fd36',
                   type='string'
                   )

    def as_dict(self):
        return self.as_dict_from_keys(['field', 'op', 'type', 'value'])

    def _get_value_as_type(self, forced_type=None):
        """Convert metadata value to the specified data type.
        """
        type = forced_type or self.type
        try:
            converted_value = self.value
            if not type:
                try:
                    converted_value = ast.literal_eval(self.value)
                except (ValueError, SyntaxError):
                    # Unable to convert the metadata value automatically
                    # let it default to self.value
                    pass
            else:
                if type not in self._supported_types:
                    # Types must be explicitly declared so the
                    # correct type converter may be used. Subclasses
                    # of Query may define _supported_types and
                    # _type_converters to define their own types.
                    raise TypeError()
                converted_value = self._type_converters[type](self.value)
        except ValueError:
            msg = (_('Unable to convert the value %(value)s'
                     ' to the expected data type %(type)s.') %
                   {'value': self.value, 'type': type})
            raise exc.ClientSideError(msg)
        except TypeError:
            msg = (_('The data type %(type)s is not supported. The supported'
                     ' data type list is: %(supported)s') %
                   {'type': type, 'supported': self._supported_types})
            raise exc.ClientSideError(msg)
        except Exception:
            msg = (_('Unexpected exception converting %(value)s to'
                     ' the expected data type %(type)s.') %
                   {'value': self.value, 'type': type})
            raise exc.ClientSideError(msg)
        return converted_value


class Pod(_Base):
    id = wtypes.text
    """ The ID of the pods."""

    name = wsme.wsattr(wtypes.text, mandatory=True)
    """ The name of the pod."""

    desc = wsme.wsattr(wtypes.text, mandatory=True)

    def __init__(self, **kwargs):
        super(Pod, self).__init__(**kwargs)

    @classmethod
    def sample(cls):
        return cls(id=str(uuid.uuid1(),
                          name="Docker",
                          desc='Docker Pods'))


class PodController(rest.RestController):
    """Manages Pods."""
    def __init__(self, **kwargs):
        super(PodController, self).__init__(**kwargs)

        self.pod_list = []

    @wsme_pecan.wsexpose(Pod, wtypes.text)
    def get_one(self, id):
        """Retrieve details about one pod.

        :param id: An ID of the pod.
        """
        for pod in self.pod_list:
            if pod.id == id:
                return self.pod
        return None

    @wsme_pecan.wsexpose([Pod], [Query], int)
    def get_all(self, q=None, limit=None):
        """Retrieve definitions of all of the pods.

        :param query: query parameters.
        :param limit: The number of pods to retrieve.
        """
        if (self.pod_list.__len__() == 0):
            return 200
        return self.pod_list

    @wsme_pecan.wsexpose(Pod, wtypes.text, wtypes.text)
    def post(self, name, type):
        """Create a new pod.

        :param pod: a pod within the request body.
        """
        pod = Pod(id=str(uuid.uuid1()), name=name, type=type)
        self.pod_list.append(pod)

        return pod

    @wsme_pecan.wsexpose(Pod, wtypes.text, body=Pod)
    def put(self, id, pod):
        """Modify this pod.

        :param id: An ID of the pod.
        :param pod: a pod within the request body.
        """
        pass

    @wsme_pecan.wsexpose(Pod, wtypes.text)
    def delete(self, id):
        """Delete this pod.

        :param id: An ID of the pod.
        """
        count = 0
        for pod in self.pod_list:
            if pod.id == id:
                self.pod_list.remove(count)
                break
            count = count + 1

        return 200
