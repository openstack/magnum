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

from magnum.objects import bay as abstract
from magnum.objects.sqlalchemy import models as sql


class Bay(sql.Base, abstract.Bay):
    """Represent an bay in sqlalchemy."""

    __tablename__ = 'bay'
    __resource__ = 'bays'
    __table_args__ = sql.table_args()

    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    uuid = sa.Column(sa.String(36), nullable=False)
    name = sa.Column(sa.String(100))
    type = sa.Column(sa.String(100))
    # workaround
    ip_address = sa.Column(sa.String(15))
    # workaround
    external_ip_address = sa.Column(sa.String(15))


class BayList(abstract.BayList):
    """Represent a list of bays in sqlalchemy."""

    @classmethod
    def get_all(cls, context):
        return BayList(sql.model_query(context, Bay))