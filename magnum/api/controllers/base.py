# All Rights Reserved.
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

import datetime
import operator
import six

from magnum.api.controllers import versions
from magnum.api import versioned_method
from magnum.common import exception
from magnum.i18n import _
from pecan import rest
from webob import exc
import wsme
from wsme import types as wtypes


# name of attribute to keep version method information
VER_METHOD_ATTR = 'versioned_methods'


class APIBase(wtypes.Base):

    created_at = wsme.wsattr(datetime.datetime, readonly=True)
    """The time in UTC at which the object is created"""

    updated_at = wsme.wsattr(datetime.datetime, readonly=True)
    """The time in UTC at which the object is updated"""

    def as_dict(self):
        """Render this object as a dict of its fields."""
        return {k: getattr(self, k)
                for k in self.fields
                if hasattr(self, k) and
                getattr(self, k) != wsme.Unset}

    def unset_fields_except(self, except_list=None):
        """Unset fields so they don't appear in the message body.

        :param except_list: A list of fields that won't be touched.

        """
        if except_list is None:
            except_list = []

        for k in self.as_dict():
            if k not in except_list:
                setattr(self, k, wsme.Unset)


class ControllerMetaclass(type):
    """Controller metaclass.

    This metaclass automates the task of assembling a dictionary
    mapping action keys to method names.
    """

    def __new__(mcs, name, bases, cls_dict):
        """Adds version function dictionary to the class."""

        versioned_methods = None

        for base in bases:
            if base.__name__ == "Controller":
                # NOTE(cyeoh): This resets the VER_METHOD_ATTR attribute
                # between API controller class creations. This allows us
                # to use a class decorator on the API methods that doesn't
                # require naming explicitly what method is being versioned as
                # it can be implicit based on the method decorated. It is a bit
                # ugly.
                if VER_METHOD_ATTR in base.__dict__:
                    versioned_methods = getattr(base, VER_METHOD_ATTR)
                    delattr(base, VER_METHOD_ATTR)

        if versioned_methods:
            cls_dict[VER_METHOD_ATTR] = versioned_methods

        return super(ControllerMetaclass, mcs).__new__(mcs, name, bases,
                                                       cls_dict)


@six.add_metaclass(ControllerMetaclass)
class Controller(rest.RestController):
    """Base Rest Controller"""

    def __getattribute__(self, key):

        def version_select():
            """Select the correct method based on version

            @return: Returns the correct versioned method
            @raises: HTTPNotAcceptable if there is no method which
                 matches the name and version constraints
            """

            from pecan import request
            ver = request.version

            func_list = self.versioned_methods[key]
            for func in func_list:
                if ver.matches(func.start_version, func.end_version):
                    return func.func

            raise exc.HTTPNotAcceptable(_(
                "Version %(ver)s was requested but the requested API %(api)s "
                "is not supported for this version.") % {'ver': ver,
                                                         'api': key})

        try:
            version_meth_dict = object.__getattribute__(self, VER_METHOD_ATTR)
        except AttributeError:
            # No versioning on this class
            return object.__getattribute__(self, key)
        if version_meth_dict and key in version_meth_dict:
            return version_select().__get__(self, self.__class__)

        return object.__getattribute__(self, key)

    # NOTE: This decorator MUST appear first (the outermost
    # decorator) on an API method for it to work correctly
    @classmethod
    def api_version(cls, min_ver, max_ver=None):
        """Decorator for versioning api methods.

        Add the decorator to any pecan method that has been exposed.
        This decorator will store the method, min version, and max
        version in a list for each api. It will check that there is no
        overlap between versions and methods. When the api is called the
        controller will use the list for each api to determine which
        method to call.

        Example:
            @base.Controller.api_version("1.1", "1.2")
            @expose.expose(Cluster, types.uuid_or_name)
            def get_one(self, cluster_ident):
            {...code for versions 1.1 to 1.2...}

            @base.Controller.api_version("1.3")
            @expose.expose(Cluster, types.uuid_or_name)
            def get_one(self, cluster_ident):
            {...code for versions 1.3 to latest}

        @min_ver: string representing minimum version
        @max_ver: optional string representing maximum version
        @raises: ApiVersionsIntersect if an version overlap is found between
            method versions.
        """

        def decorator(f):
            obj_min_ver = versions.Version('', '', '', min_ver)
            if max_ver:
                obj_max_ver = versions.Version('', '', '', max_ver)
            else:
                obj_max_ver = versions.Version('', '', '',
                                               versions.CURRENT_MAX_VER)

            # Add to list of versioned methods registered
            func_name = f.__name__
            new_func = versioned_method.VersionedMethod(
                func_name, obj_min_ver, obj_max_ver, f)

            func_dict = getattr(cls, VER_METHOD_ATTR, {})
            if not func_dict:
                setattr(cls, VER_METHOD_ATTR, func_dict)

            func_list = func_dict.get(func_name, [])
            if not func_list:
                func_dict[func_name] = func_list
            func_list.append(new_func)

            is_intersect = Controller.check_for_versions_intersection(
                func_list)

            if is_intersect:
                raise exception.ApiVersionsIntersect(
                    name=new_func.name,
                    min_ver=new_func.start_version,
                    max_ver=new_func.end_version
                )

            # Ensure the list is sorted by minimum version (reversed)
            # so later when we work through the list in order we find
            # the method which has the latest version which supports
            # the version requested.
            func_list.sort(key=lambda f: f.start_version, reverse=True)

            return f

        return decorator

    @staticmethod
    def check_for_versions_intersection(func_list):
        """Determines whether function list intersections

        General algorithm:
        https://en.wikipedia.org/wiki/Intersection_algorithm

        :param func_list: list of VersionedMethod objects
        :return: boolean
        """

        pairs = []
        counter = 0

        for f in func_list:
            pairs.append((f.start_version, 1))
            pairs.append((f.end_version, -1))

        pairs.sort(key=operator.itemgetter(1), reverse=True)
        pairs.sort(key=operator.itemgetter(0))

        for p in pairs:
            counter += p[1]

            if counter > 1:
                return True

        return False
