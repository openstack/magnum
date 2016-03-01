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
        return {k: getattr(self, k)
                for k in self.fields
                if self.obj_attr_is_set(k)}


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


class MagnumObjectIndirectionAPI(ovoo_base.VersionedObjectIndirectionAPI):
    def __init__(self):
        super(MagnumObjectIndirectionAPI, self).__init__()
        from magnum.conductor import api as conductor_api
        self._conductor = conductor_api.API()

    def object_action(self, context, objinst, objmethod, args, kwargs):
        return self._conductor.object_action(context, objinst, objmethod,
                                             args, kwargs)

    def object_class_action(self, context, objname, objmethod, objver,
                            args, kwargs):
        return self._conductor.object_class_action(context, objname, objmethod,
                                                   objver, args, kwargs)

    def object_backport(self, context, objinst, target_version):
        return self._conductor.object_backport(context, objinst,
                                               target_version)


class MagnumObjectSerializer(ovoo_base.VersionedObjectSerializer):
    # Base class to use for object hydration
    OBJ_BASE_CLASS = MagnumObject
