# Copyright 2015 Huawei Technologies Co.,LTD.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import decorator
import pecan

from magnum.common import exception
from magnum import objects


def enforce_bay_types(*bay_types):
    def decorate(func):
        @decorator.decorator
        def handler(func, *args, **kwargs):
            obj = args[1]
            bay = objects.Bay.get_by_uuid(pecan.request.context, obj.bay_uuid)
            baymodel = objects.BayModel.get_by_uuid(pecan.request.context,
                                                    bay.baymodel_id)
            if baymodel.coe not in bay_types:
                raise exception.InvalidParameterValue(
                    'Cannot fulfill request with a %(bay_type)s bay, '
                    'expecting a %(supported_bay_types)s bay.' %
                    {'bay_type': baymodel.coe,
                     'supported_bay_types': '/'.join(bay_types)})

            return func(*args, **kwargs)
        return handler(func)

    return decorate
