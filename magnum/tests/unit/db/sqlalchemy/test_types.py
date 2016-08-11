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

"""Tests for custom SQLAlchemy types via Magnum DB."""

from oslo_db import exception as db_exc
from oslo_utils import uuidutils

import magnum.db.sqlalchemy.api as sa_api
from magnum.db.sqlalchemy import models
from magnum.tests.unit.db import base


class SqlAlchemyCustomTypesTestCase(base.DbTestCase):

    def test_JSONEncodedDict_default_value(self):
        # Create baymodel w/o labels
        baymodel1_id = uuidutils.generate_uuid()
        self.dbapi.create_baymodel({'uuid': baymodel1_id})
        baymodel1 = sa_api.model_query(
            models.BayModel).filter_by(uuid=baymodel1_id).one()
        self.assertEqual({}, baymodel1.labels)

        # Create baymodel with labels
        baymodel2_id = uuidutils.generate_uuid()
        self.dbapi.create_baymodel(
            {'uuid': baymodel2_id, 'labels': {'bar': 'foo'}})
        baymodel2 = sa_api.model_query(
            models.BayModel).filter_by(uuid=baymodel2_id).one()
        self.assertEqual('foo', baymodel2.labels['bar'])

    def test_JSONEncodedDict_type_check(self):
        self.assertRaises(db_exc.DBError,
                          self.dbapi.create_baymodel,
                          {'labels':
                           ['this is not a dict']})

    def test_JSONEncodedList_default_value(self):
        # Create bay w/o master_addresses
        bay1_id = uuidutils.generate_uuid()
        self.dbapi.create_bay({'uuid': bay1_id})
        bay1 = sa_api.model_query(
            models.Bay).filter_by(uuid=bay1_id).one()
        self.assertEqual([], bay1.master_addresses)

        # Create bay with master_addresses
        bay2_id = uuidutils.generate_uuid()
        self.dbapi.create_bay({'uuid': bay2_id,
                              'master_addresses': ['mymaster_address1',
                                                   'mymaster_address2']})
        bay2 = sa_api.model_query(
            models.Bay).filter_by(uuid=bay2_id).one()
        self.assertEqual(['mymaster_address1', 'mymaster_address2'],
                         bay2.master_addresses)

    def test_JSONEncodedList_type_check(self):
        self.assertRaises(db_exc.DBError,
                          self.dbapi.create_bay,
                          {'master_addresses':
                           {'this is not a list': 'test'}})
