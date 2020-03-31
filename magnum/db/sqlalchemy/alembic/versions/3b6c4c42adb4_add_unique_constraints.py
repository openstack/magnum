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

"""Add unique constraints

Revision ID: 3b6c4c42adb4
Revises: 592131657ca1
Create Date: 2015-05-05 09:45:44.657047

"""

# revision identifiers, used by Alembic.
revision = '3b6c4c42adb4'
down_revision = '592131657ca1'

from alembic import op  # noqa: E402


def upgrade():
    op.create_unique_constraint("uniq_bay0uuid", "bay", ["uuid"])
    op.create_unique_constraint("uniq_baylock0bay_uuid", "baylock",
                                ["bay_uuid"])
    op.create_unique_constraint("uniq_baymodel0uuid", "baymodel", ["uuid"])
    op.create_unique_constraint("uniq_container0uuid", "container", ["uuid"])
    op.create_unique_constraint("uniq_node0uuid", "node", ["uuid"])
    op.create_unique_constraint("uniq_node0ironic_node_id", "node",
                                ["ironic_node_id"])
    op.create_unique_constraint("uniq_pod0uuid", "pod", ["uuid"])
    op.create_unique_constraint("uniq_service0uuid", "service", ["uuid"])
    op.create_unique_constraint("uniq_replicationcontroller0uuid",
                                "replicationcontroller", ["uuid"])
