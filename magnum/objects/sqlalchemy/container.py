# Copyright 2014 NEC Corporation.  All rights reserved.
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

import sqlalchemy as sa

from magnum.objects.sqlalchemy import models as sql


class Container(sql.Base):
    """Represent an container in sqlalchemy."""

    __tablename__ = 'container'
    __resource__ = 'containers'
    __table_args__ = sql.table_args()

    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    uuid = sa.Column(sa.String(36), nullable=False)
    # pod_id = sa.Column(sa.String(36))
    name = sa.Column(sa.String(100))
    dns = sa.Column(sql.JSONEncodedList)
    image = sa.Column(sa.String(100))
    # command: ['nc', '-p', '8080', '-l', '-l', '-e', 'echo', 'hello world!']
    command = sa.Column(sql.JSONEncodedList)
    # The initial working directory for the command.
    workdir = sa.Column(sa.String(1023))
    # [
    #     {
    #         "container_path": "/path/to/guest/path",
    #         "host_path": "/path/to/host/dir"
    #     }
    # ]
    volumes = sa.Column(sql.JSONEncodedList)
    # [ { "container_port": 80, "host_port": 8080 } ]
    ports = sa.Column(sql.JSONEncodedList)
    env = sa.Column(sql.JSONEncodedDict)
    # [ { "name": "name of container", "alias": "alias for the link name"} ]
    links = sa.Column(sql.JSONEncodedDict)


class ContainerList():
    """Represent a list of containers in sqlalchemy."""

    @classmethod
    def get_all(cls, context):
        return ContainerList(sql.model_query(context, Container))
