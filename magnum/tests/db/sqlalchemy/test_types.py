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

from oslo.db import exception as db_exc

from magnum.common import utils as magnum_utils
from magnum.db import api as dbapi
import magnum.db.sqlalchemy.api as sa_api
from magnum.db.sqlalchemy import models
from magnum.tests.db import base


class SqlAlchemyCustomTypesTestCase(base.DbTestCase):

    def setUp(self):
        super(SqlAlchemyCustomTypesTestCase, self).setUp()
        self.dbapi = dbapi.get_instance()

    def test_JSONEncodedDict_default_value(self):
        # Create pod w/o labels
        pod1_id = magnum_utils.generate_uuid()
        self.dbapi.create_pod({'uuid': pod1_id})
        pod1 = sa_api.model_query(models.Pod).filter_by(uuid=pod1_id).one()
        self.assertEqual({}, pod1.labels)

        # Create pod with labels
        pod2_id = magnum_utils.generate_uuid()
        self.dbapi.create_pod({'uuid': pod2_id, 'labels': {'bar': 'foo'}})
        pod2 = sa_api.model_query(models.Pod).filter_by(uuid=pod2_id).one()
        self.assertEqual('foo', pod2.labels['bar'])

    def test_JSONEncodedDict_type_check(self):
        self.assertRaises(db_exc.DBError,
                          self.dbapi.create_pod,
                          {'labels':
                               ['this is not a dict']})

    def test_JSONEncodedList_default_value(self):
        # Create pod w/o images
        pod1_id = magnum_utils.generate_uuid()
        self.dbapi.create_pod({'uuid': pod1_id})
        pod1 = sa_api.model_query(models.Pod).filter_by(uuid=pod1_id).one()
        self.assertEqual([], pod1.images)

        # Create pod with images
        pod2_id = magnum_utils.generate_uuid()
        self.dbapi.create_pod({'uuid': pod2_id,
                               'images': ['myimage1', 'myimage2']})
        pod2 = sa_api.model_query(models.Pod).filter_by(uuid=pod2_id).one()
        self.assertEqual(['myimage1', 'myimage2'], pod2.images)

    def test_JSONEncodedList_type_check(self):
        self.assertRaises(db_exc.DBError,
                          self.dbapi.create_pod,
                          {'images':
                               {'this is not a list': 'test'}})
