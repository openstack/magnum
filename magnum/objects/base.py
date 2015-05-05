#    Copyright 2013 IBM Corp.
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

"""Magnum common internal object model"""

import collections

from oslo_context import context as oslo_context
from oslo_versionedobjects import base as ovoo_base
from oslo_versionedobjects import fields as ovoo_fields
import six

from magnum.common import exception
from magnum.openstack.common._i18n import _
from magnum.openstack.common._i18n import _LE
from magnum.openstack.common import log as logging
from magnum.openstack.common import versionutils


LOG = logging.getLogger('object')


class MagnumObjectMetaclass(type):
    """Metaclass that allows tracking of object classes."""

    # NOTE(danms): This is what controls whether object operations are
    # remoted. If this is not None, use it to remote things over RPC.
    indirection_api = None

    def __init__(cls, names, bases, dict_):
        if not hasattr(cls, '_obj_classes'):
            # This will be set in the 'MagnumObject' class.
            cls._obj_classes = collections.defaultdict(list)
        else:
            # Add the subclass to MagnumObject._obj_classes
            ovoo_base._make_class_properties(cls)
            cls._obj_classes[cls.obj_name()].append(cls)
            # NOTE(xek): object tracking will be moved to a new registartion
            # scheme from oslo.versionedobjects, which uses decorators


# These are decorators that mark an object's method as remotable.
# If the metaclass is configured to forward object methods to an
# indirection service, these will result in making an RPC call
# instead of directly calling the implementation in the object. Instead,
# the object implementation on the remote end will perform the
# requested action and the result will be returned here.
def remotable_classmethod(fn):
    """Decorator for remotable classmethods."""
    def wrapper(cls, context, *args, **kwargs):
        if MagnumObject.indirection_api:
            result = MagnumObject.indirection_api.object_class_action(
                context, cls.obj_name(), fn.__name__, cls.VERSION,
                args, kwargs)
        else:
            result = fn(cls, context, *args, **kwargs)
            if isinstance(result, MagnumObject):
                result._context = context
        return result
    return classmethod(wrapper)


# See comment above for remotable_classmethod()
#
# Note that this will use either the provided context, or the one
# stashed in the object. If neither are present, the object is
# "orphaned" and remotable methods cannot be called.
def remotable(fn):
    """Decorator for remotable object methods."""
    def wrapper(self, *args, **kwargs):
        context = self._context
        try:
            if isinstance(args[0], (oslo_context.RequestContext)):
                context = args[0]
                args = args[1:]
        except IndexError:
            pass
        if context is None:
            raise exception.OrphanedObjectError(method=fn.__name__,
                                                objtype=self.obj_name())
        if MagnumObject.indirection_api:
            updates, result = MagnumObject.indirection_api.object_action(
                context, self, fn.__name__, args, kwargs)
            for key, value in updates.iteritems():
                if key in self.fields:
                    field = self.fields[key]
                    self[key] = field.from_primitive(self, key, value)
            self._changed_fields = set(updates.get('obj_what_changed', []))
            return result
        else:
            return fn(self, context, *args, **kwargs)
    return wrapper


# Object versioning rules
#
# Each service has its set of objects, each with a version attached. When
# a client attempts to call an object method, the server checks to see if
# the version of that object matches (in a compatible way) its object
# implementation. If so, cool, and if not, fail.
def check_object_version(server, client):
    try:
        client_major, _client_minor = client.split('.')
        server_major, _server_minor = server.split('.')
        client_minor = int(_client_minor)
        server_minor = int(_server_minor)
    except ValueError:
        raise exception.IncompatibleObjectVersion(
            _('Invalid version string'))

    if client_major != server_major:
        raise exception.IncompatibleObjectVersion(
            dict(client=client_major, server=server_major))
    if client_minor > server_minor:
        raise exception.IncompatibleObjectVersion(
            dict(client=client_minor, server=server_minor))


@six.add_metaclass(MagnumObjectMetaclass)
class MagnumObject(ovoo_base.VersionedObject):
    """Base class and object factory.

    This forms the base of all objects that can be remoted or instantiated
    via RPC. Simply defining a class that inherits from this base class
    will make it remotely instantiatable. Objects should implement the
    necessary "get" classmethod routines as well as "save" object methods
    as appropriate.
    """

    OBJ_SERIAL_NAMESPACE = 'magnum_object'
    OBJ_PROJECT_NAMESPACE = 'magnum'

    @classmethod
    def obj_class_from_name(cls, objname, objver):
        """Returns a class from the registry based on a name and version."""
        if objname not in cls._obj_classes:
            LOG.error(_LE('Unable to instantiate unregistered object type '
                          '%(objtype)s'), dict(objtype=objname))
            raise exception.UnsupportedObjectError(objtype=objname)

        latest = None
        compatible_match = None
        for objclass in cls._obj_classes[objname]:
            if objclass.VERSION == objver:
                return objclass

            version_bits = tuple([int(x) for x in objclass.VERSION.split(".")])
            if latest is None:
                latest = version_bits
            elif latest < version_bits:
                latest = version_bits

            if versionutils.is_compatible(objver, objclass.VERSION):
                compatible_match = objclass

        if compatible_match:
            return compatible_match

        latest_ver = '%i.%i' % latest
        raise exception.IncompatibleObjectVersion(objname=objname,
                                                  objver=objver,
                                                  supported=latest_ver)

    def as_dict(self):
        return dict((k, getattr(self, k))
                    for k in self.fields
                    if hasattr(self, k))


class MagnumObjectDictCompat(ovoo_base.VersionedObjectDictCompat):
    pass


class MagnumPersistentObject(object):
    """Mixin class for Persistent objects.
    This adds the fields that we use in common for all persistent objects.
    """
    fields = {
        'created_at': ovoo_fields.DateTimeField(nullable=True),
        'updated_at': ovoo_fields.DateTimeField(nullable=True),
        }


class ObjectListBase(ovoo_base.ObjectListBase):
    # TODO(xek): These are for transition to using the oslo base object
    # and can be removed when we move to it.
    fields = {
        'objects': list,
    }

    def _attr_objects_to_primitive(self):
        """Serialization of object list."""
        return [x.obj_to_primitive() for x in self.objects]

    def _attr_objects_from_primitive(self, value):
        """Deserialization of object list."""
        objects = []
        for entity in value:
            obj = MagnumObject.obj_from_primitive(entity,
                                                  context=self._context)
            objects.append(obj)
        return objects


class MagnumObjectSerializer(ovoo_base.VersionedObjectSerializer):
    # Base class to use for object hydration
    OBJ_BASE_CLASS = MagnumObject


def obj_to_primitive(obj):
    """Recursively turn an object into a python primitive.

    An MagnumObject becomes a dict, and anything that implements ObjectListBase
    becomes a list.
    """
    if isinstance(obj, ObjectListBase):
        return [obj_to_primitive(x) for x in obj]
    elif isinstance(obj, MagnumObject):
        result = {}
        for key in obj.obj_fields:
            if obj.obj_attr_is_set(key) or key in obj.obj_extra_fields:
                result[key] = obj_to_primitive(getattr(obj, key))
        return result
    else:
        return obj
