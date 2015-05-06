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

from oslo_versionedobjects import base as ovoo_base
from oslo_versionedobjects import fields as ovoo_fields

from magnum.openstack.common import log as logging

LOG = logging.getLogger('object')

remotable_classmethod = ovoo_base.remotable_classmethod
remotable = ovoo_base.remotable


class MagnumObjectRegistry(ovoo_base.VersionedObjectRegistry):
    pass


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
