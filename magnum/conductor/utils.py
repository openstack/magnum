# Copyright 2015 Huawei Technologies Co.,LTD.
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

from magnum.common import clients
from magnum import objects


def retrieve_bay(context, obj):
    return objects.Bay.get_by_uuid(context, obj.bay_uuid)


def retrieve_baymodel(context, bay):
    return objects.BayModel.get_by_uuid(context, bay.baymodel_id)


def object_has_stack(context, obj):
    osc = clients.OpenStackClients(context)
    if hasattr(obj, 'bay_uuid'):
        obj = retrieve_bay(context, obj)

    stack = osc.heat().stacks.get(obj.stack_id)
    if (stack.stack_status == 'DELETE_COMPLETE' or
            stack.stack_status == 'DELETE_IN_PROGRESS'):
        return False

    return True
