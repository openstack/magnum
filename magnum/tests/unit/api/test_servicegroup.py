# Licensed under the Apache License, Version 2.0 (the "License"); you may not
# use this file except in compliance with the License. You may obtain a copy
# of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import datetime
from unittest import mock

from oslo_utils import timeutils
import pytz

from magnum.api import servicegroup as svc_grp
from magnum.tests.unit.api import base as api_base
from magnum.tests.unit.objects import utils as obj_util


class TestServiceGroup(api_base.FunctionalTest):
    def setUp(self):
        super(TestServiceGroup, self).setUp()
        self.servicegroup_api = svc_grp.ServiceGroup()

    def test_service_is_up_check_type(self):
        random_obj = mock.MagicMock()
        self.assertRaises(TypeError,
                          self.servicegroup_api.service_is_up, random_obj)

    def test_service_is_up_forced_down(self):
        kwarg = {'forced_down': True}
        magnum_object = obj_util.get_test_magnum_service_object(
            self.context, **kwarg)
        is_up = self.servicegroup_api.service_is_up(magnum_object)
        self.assertFalse(is_up)

    def test_service_is_up_alive(self):
        kwarg = {'last_seen_up': timeutils.utcnow(True)}
        magnum_object = obj_util.get_test_magnum_service_object(
            self.context, **kwarg)
        is_up = self.servicegroup_api.service_is_up(magnum_object)
        self.assertTrue(is_up)

    def test_service_is_up_alive_with_created(self):
        kwarg = {'created_at': timeutils.utcnow(True)}
        magnum_object = obj_util.get_test_magnum_service_object(
            self.context, **kwarg)
        is_up = self.servicegroup_api.service_is_up(magnum_object)
        self.assertTrue(is_up)

    def test_service_is_up_alive_with_updated(self):
        kwarg = {'updated_at': timeutils.utcnow(True)}
        magnum_object = obj_util.get_test_magnum_service_object(
            self.context, **kwarg)
        is_up = self.servicegroup_api.service_is_up(magnum_object)
        self.assertTrue(is_up)

    def test_service_is_up_alive_with_all_three(self):
        kwarg = {'created_at': timeutils.utcnow(True),
                 'updated_at': timeutils.utcnow(True),
                 'last_seen_up': timeutils.utcnow(True)}
        magnum_object = obj_util.get_test_magnum_service_object(
            self.context, **kwarg)
        is_up = self.servicegroup_api.service_is_up(magnum_object)
        self.assertTrue(is_up)

    def test_service_is_up_alive_with_latest_update(self):
        kwarg = {'created_at': datetime.datetime(1970, 1, 1,
                                                 tzinfo=pytz.UTC),
                 'updated_at': datetime.datetime(1970, 1, 1,
                                                 tzinfo=pytz.UTC),
                 'last_seen_up': timeutils.utcnow(True)}
        magnum_object = obj_util.get_test_magnum_service_object(
            self.context, **kwarg)
        is_up = self.servicegroup_api.service_is_up(magnum_object)
        self.assertTrue(is_up)

    def test_service_is_up_down(self):
        kwarg = {'last_seen_up': datetime.datetime(1970, 1, 1,
                                                   tzinfo=pytz.UTC)}
        magnum_object = obj_util.get_test_magnum_service_object(
            self.context, **kwarg)
        is_up = self.servicegroup_api.service_is_up(magnum_object)
        self.assertFalse(is_up)

    def test_service_is_up_down_with_create(self):
        kwarg = {'created_at': datetime.datetime(1970, 1, 1,
                                                 tzinfo=pytz.UTC)}
        magnum_object = obj_util.get_test_magnum_service_object(
            self.context, **kwarg)
        is_up = self.servicegroup_api.service_is_up(magnum_object)
        self.assertFalse(is_up)

    def test_service_is_up_down_with_update(self):
        kwarg = {'updated_at': datetime.datetime(1970, 1, 1,
                                                 tzinfo=pytz.UTC)}
        magnum_object = obj_util.get_test_magnum_service_object(
            self.context, **kwarg)
        is_up = self.servicegroup_api.service_is_up(magnum_object)
        self.assertFalse(is_up)

    def test_service_is_up_down_with_all_three(self):
        kwarg = {'last_seen_up': datetime.datetime(1970, 1, 1,
                                                   tzinfo=pytz.UTC),
                 'created_at': datetime.datetime(1970, 1, 1,
                                                 tzinfo=pytz.UTC),
                 'updated_at': datetime.datetime(1970, 1, 1,
                                                 tzinfo=pytz.UTC)}
        magnum_object = obj_util.get_test_magnum_service_object(
            self.context, **kwarg)
        is_up = self.servicegroup_api.service_is_up(magnum_object)
        self.assertFalse(is_up)

    def test_service_is_up_down_with_old_update(self):
        kwarg = {'last_seen_up': datetime.datetime(1970, 1, 1,
                                                   tzinfo=pytz.UTC),
                 'created_at': timeutils.utcnow(True),
                 'updated_at': timeutils.utcnow(True)}
        magnum_object = obj_util.get_test_magnum_service_object(
            self.context, **kwarg)
        is_up = self.servicegroup_api.service_is_up(magnum_object)
        self.assertFalse(is_up)
