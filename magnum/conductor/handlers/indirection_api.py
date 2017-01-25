# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

import oslo_messaging as messaging

from magnum.common import profiler
from magnum.objects import base


@profiler.trace_cls("rpc")
class Handler(object):
    "Indirection API callbacks"

    def _object_dispatch(self, target, method, context, args, kwargs):
        """Dispatch a call to an object method.

        This ensures that object methods get called and any exception
        that is raised gets wrapped in an ExpectedException for forwarding
        back to the caller (without spamming the conductor logs).
        """
        try:
            # NOTE(danms): Keep the getattr inside the try block since
            # a missing method is really a client problem
            return getattr(target, method)(context, *args, **kwargs)
        except Exception:
            raise messaging.ExpectedException()

    def object_class_action(self, context, objname, objmethod,
                            objver, args, kwargs):
        """Perform a classmethod action on an object."""
        objclass = base.MagnumObject.obj_class_from_name(objname, objver)
        result = self._object_dispatch(objclass, objmethod, context,
                                       args, kwargs)
        # NOTE(danms): The RPC layer will convert to primitives for us,
        # but in this case, we need to honor the version the client is
        # asking for, so we do it before returning here.
        return (result.obj_to_primitive(target_version=objver)
                if isinstance(result, base.MagnumObject) else result)

    def object_action(self, context, objinst, objmethod, args, kwargs):
        """Perform an action on an object."""
        old_objinst = objinst.obj_clone()
        result = self._object_dispatch(objinst, objmethod, context,
                                       args, kwargs)
        updates = dict()
        # NOTE(danms): Diff the object with the one passed to us and
        # generate a list of changes to forward back
        for name, field in objinst.fields.items():
            if not objinst.obj_attr_is_set(name):
                # Avoid demand-loading anything
                continue
            if (not old_objinst.obj_attr_is_set(name) or
                    getattr(old_objinst, name) != getattr(objinst, name)):
                updates[name] = field.to_primitive(objinst, name,
                                                   getattr(objinst, name))
        updates['obj_what_changed'] = objinst.obj_what_changed()
        return updates, result

    def object_backport(self, context, objinst, target_version):
        return objinst.obj_to_primitive(target_version=target_version)
