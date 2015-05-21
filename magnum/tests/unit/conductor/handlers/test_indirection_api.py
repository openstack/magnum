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

import oslo_messaging as messaging
from oslo_versionedobjects import fields

from magnum.conductor.handlers import indirection_api
from magnum.objects import base as obj_base
from magnum.tests import base


class TestIndirectionApiConductor(base.TestCase):
    def setUp(self):
        super(TestIndirectionApiConductor, self).setUp()
        self.conductor = indirection_api.Handler()

    def _test_object_action(self, is_classmethod, raise_exception):
        @obj_base.MagnumObjectRegistry.register
        class TestObject(obj_base.MagnumObject):
            def foo(self, context, raise_exception=False):
                if raise_exception:
                    raise Exception('test')
                else:
                    return 'test'

            @classmethod
            def bar(cls, context, raise_exception=False):
                if raise_exception:
                    raise Exception('test')
                else:
                    return 'test'

        obj = TestObject()
        if is_classmethod:
            result = self.conductor.object_class_action(
                self.context, TestObject.obj_name(), 'bar', '1.0',
                tuple(), {'raise_exception': raise_exception})
        else:
            updates, result = self.conductor.object_action(
                self.context, obj, 'foo', tuple(),
                {'raise_exception': raise_exception})
        self.assertEqual('test', result)

    def test_object_action(self):
        self._test_object_action(False, False)

    def test_object_action_on_raise(self):
        self.assertRaises(messaging.ExpectedException,
                          self._test_object_action, False, True)

    def test_object_class_action(self):
        self._test_object_action(True, False)

    def test_object_class_action_on_raise(self):
        self.assertRaises(messaging.ExpectedException,
                          self._test_object_action, True, True)

    def test_object_action_copies_object(self):
        @obj_base.MagnumObjectRegistry.register
        class TestObject(obj_base.MagnumObject):
            fields = {'dict': fields.DictOfStringsField()}

            def touch_dict(self, context):
                self.dict['foo'] = 'bar'
                self.obj_reset_changes()

        obj = TestObject()
        obj.dict = {}
        obj.obj_reset_changes()
        updates, result = self.conductor.object_action(
            self.context, obj, 'touch_dict', tuple(), {})
        # NOTE(danms): If conductor did not properly copy the object, then
        # the new and reference copies of the nested dict object will be
        # the same, and thus 'dict' will not be reported as changed
        self.assertIn('dict', updates)
        self.assertEqual({'foo': 'bar'}, updates['dict'])
