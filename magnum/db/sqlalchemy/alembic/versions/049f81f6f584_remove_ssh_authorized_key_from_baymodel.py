# Copyright 2016 Huawei Technologies Co.,LTD.
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

"""remove_ssh_authorized_key_from_baymodel

Revision ID: 049f81f6f584
Revises: ee92b41b8809
Create Date: 2016-02-28 15:27:26.211244

"""

# revision identifiers, used by Alembic.
revision = '049f81f6f584'
down_revision = 'ee92b41b8809'

from alembic import op  # noqa: E402


def upgrade():
    op.drop_column('baymodel', 'ssh_authorized_key')
