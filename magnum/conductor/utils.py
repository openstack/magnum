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
from magnum.common import utils
from magnum.objects import bay
from magnum.objects import baymodel


def retrieve_bay(context, bay_ident):
    if not utils.is_uuid_like(bay_ident):
        return bay.Bay.get_by_name(context, bay_ident)
    else:
        return bay.Bay.get_by_uuid(context, bay_ident)


def retrieve_baymodel(context, bay):
    return baymodel.BayModel.get_by_uuid(context, bay.baymodel_id)


def retrieve_bay_uuid(context, bay_ident):
    if not utils.is_uuid_like(bay_ident):
        bay_obj = bay.Bay.get_by_name(context, bay_ident)
        return bay_obj.uuid
    else:
        return bay_ident


def object_has_stack(context, bay_uuid):
    osc = clients.OpenStackClients(context)
    obj = retrieve_bay(context, bay_uuid)

    stack = osc.heat().stacks.get(obj.stack_id)
    if (stack.stack_status == 'DELETE_COMPLETE' or
            stack.stack_status == 'DELETE_IN_PROGRESS'):
        return False

    return True
