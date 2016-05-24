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
        # Create rc w/o labels
        rc1_id = uuidutils.generate_uuid()
        self.dbapi.create_rc({'uuid': rc1_id})
        rc1 = sa_api.model_query(
            models.ReplicationController).filter_by(uuid=rc1_id).one()
        self.assertEqual({}, rc1.labels)

        # Create rc with labels
        rc2_id = uuidutils.generate_uuid()
        self.dbapi.create_rc({'uuid': rc2_id, 'labels': {'bar': 'foo'}})
        rc2 = sa_api.model_query(
            models.ReplicationController).filter_by(uuid=rc2_id).one()
        self.assertEqual('foo', rc2.labels['bar'])

    def test_JSONEncodedDict_type_check(self):
        self.assertRaises(db_exc.DBError,
                          self.dbapi.create_rc,
                          {'labels':
                           ['this is not a dict']})

    def test_JSONEncodedList_default_value(self):
        # Create rc w/o images
        rc1_id = uuidutils.generate_uuid()
        self.dbapi.create_rc({'uuid': rc1_id})
        rc1 = sa_api.model_query(
            models.ReplicationController).filter_by(uuid=rc1_id).one()
        self.assertEqual([], rc1.images)

        # Create rc with images
        rc2_id = uuidutils.generate_uuid()
        self.dbapi.create_rc({'uuid': rc2_id,
                              'images': ['myimage1', 'myimage2']})
        rc2 = sa_api.model_query(
            models.ReplicationController).filter_by(uuid=rc2_id).one()
        self.assertEqual(['myimage1', 'myimage2'], rc2.images)

    def test_JSONEncodedList_type_check(self):
        self.assertRaises(db_exc.DBError,
                          self.dbapi.create_rc,
                          {'images':
                           {'this is not a list': 'test'}})
