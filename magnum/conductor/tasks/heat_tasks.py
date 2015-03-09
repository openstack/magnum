# Copyright 2015 NEC Corporation.  All rights reserved.
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

from magnum.conductor import tasks


class CreateStack(tasks.OSBaseTask):
    """CreateStack Task

    This task interfaces with Heat API and creates a stack based on parameters
    provided to the Task.

    """

    def execute(self, stack_name, parameters, template, files):
        stack = self.os_client.stacks.create(stack_name=stack_name,
                                             parameters=parameters,
                                             template=template, files=files)
        return stack


class UpdateStack(tasks.OSBaseTask):
    """UpdateStack Task

    This task interfaces with Heat API and update a stack based on parameters
    provided to the Task.

    """

    def execute(self, stack_id, parameters, template, files):
        self.os_client.stacks.update(stack_id, parameters=parameters,
                                     template=template, files=files)


class DeleteStack(tasks.OSBaseTask):
    """DeleteStack Task

    This task interfaces with Heat API and delete a stack based on parameters
    provided to the Task.

    """

    def execute(self, stack_id):
        self.os_client.stacks.delete(stack_id)
