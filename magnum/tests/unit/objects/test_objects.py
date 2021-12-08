#    Copyright 2015 IBM Corp.
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

import datetime
import gettext
from unittest import mock

from oslo_versionedobjects import exception as object_exception
from oslo_versionedobjects import fields
from oslo_versionedobjects import fixture

from magnum.common import context as magnum_context
from magnum.objects import base
from magnum.tests import base as test_base

gettext.install('magnum')


@base.MagnumObjectRegistry.register
class MyObj(base.MagnumPersistentObject, base.MagnumObject):
    VERSION = '1.0'

    fields = {'foo': fields.IntegerField(),
              'bar': fields.StringField(),
              'missing': fields.StringField(),
              }

    def obj_load_attr(self, attrname):
        setattr(self, attrname, 'loaded!')

    @base.remotable_classmethod
    def query(cls, context):
        obj = cls(context)
        obj.foo = 1
        obj.bar = 'bar'
        obj.obj_reset_changes()
        return obj

    @base.remotable
    def marco(self, context):
        return 'polo'

    @base.remotable
    def update_test(self, context):
        if context.project_id == 'alternate':
            self.bar = 'alternate-context'
        else:
            self.bar = 'updated'

    @base.remotable
    def save(self, context):
        self.obj_reset_changes()

    @base.remotable
    def refresh(self, context):
        self.foo = 321
        self.bar = 'refreshed'
        self.obj_reset_changes()

    @base.remotable
    def modify_save_modify(self, context):
        self.bar = 'meow'
        self.save(context)
        self.foo = 42


class MyObj2(object):
    @classmethod
    def obj_name(cls):
        return 'MyObj'

    @base.remotable_classmethod
    def get(cls, *args, **kwargs):
        pass


@base.MagnumObjectRegistry.register_if(False)
class TestSubclassedObject(MyObj):
    fields = {'new_field': fields.StringField()}


class _TestObject(object):
    def test_hydration_type_error(self):
        primitive = {'magnum_object.name': 'MyObj',
                     'magnum_object.namespace': 'magnum',
                     'magnum_object.version': '1.0',
                     'magnum_object.data': {'foo': 'a'}}
        self.assertRaises(ValueError, MyObj.obj_from_primitive, primitive)

    def test_hydration(self):
        primitive = {'magnum_object.name': 'MyObj',
                     'magnum_object.namespace': 'magnum',
                     'magnum_object.version': '1.0',
                     'magnum_object.data': {'foo': 1}}
        obj = MyObj.obj_from_primitive(primitive)
        self.assertEqual(1, obj.foo)

    def test_hydration_bad_ns(self):
        primitive = {'magnum_object.name': 'MyObj',
                     'magnum_object.namespace': 'foo',
                     'magnum_object.version': '1.0',
                     'magnum_object.data': {'foo': 1}}
        self.assertRaises(object_exception.UnsupportedObjectError,
                          MyObj.obj_from_primitive, primitive)

    def test_dehydration(self):
        expected = {'magnum_object.name': 'MyObj',
                    'magnum_object.namespace': 'magnum',
                    'magnum_object.version': '1.0',
                    'magnum_object.data': {'foo': 1}}
        obj = MyObj(self.context)
        obj.foo = 1
        obj.obj_reset_changes()
        self.assertEqual(expected, obj.obj_to_primitive())

    def test_get_updates(self):
        obj = MyObj(self.context)
        self.assertEqual({}, obj.obj_get_changes())
        obj.foo = 123
        self.assertEqual({'foo': 123}, obj.obj_get_changes())
        obj.bar = 'test'
        self.assertEqual({'foo': 123, 'bar': 'test'}, obj.obj_get_changes())
        obj.obj_reset_changes()
        self.assertEqual({}, obj.obj_get_changes())

    def test_object_property(self):
        obj = MyObj(self.context, foo=1)
        self.assertEqual(1, obj.foo)

    def test_object_property_type_error(self):
        obj = MyObj(self.context)

        def fail():
            obj.foo = 'a'
        self.assertRaises(ValueError, fail)

    def test_load(self):
        obj = MyObj(self.context)
        self.assertEqual('loaded!', obj.bar)

    def test_load_in_base(self):
        @base.MagnumObjectRegistry.register_if(False)
        class Foo(base.MagnumPersistentObject, base.MagnumObject):
            fields = {'foobar': fields.IntegerField()}
        obj = Foo(self.context)
        # NOTE(danms): Can't use assertRaisesRegexp() because of py26
        raised = False
        ex = None
        try:
            obj.foobar
        except NotImplementedError as e:
            raised = True
            ex = e
        self.assertTrue(raised)
        self.assertIn('foobar', str(ex))

    def test_loaded_in_primitive(self):
        obj = MyObj(self.context)
        obj.foo = 1
        obj.obj_reset_changes()
        self.assertEqual('loaded!', obj.bar)
        expected = {'magnum_object.name': 'MyObj',
                    'magnum_object.namespace': 'magnum',
                    'magnum_object.version': '1.0',
                    'magnum_object.changes': ['bar'],
                    'magnum_object.data': {'foo': 1,
                                           'bar': 'loaded!'}}
        self.assertEqual(expected, obj.obj_to_primitive())

    def test_changes_in_primitive(self):
        obj = MyObj(self.context)
        obj.foo = 123
        self.assertEqual(set(['foo']), obj.obj_what_changed())
        primitive = obj.obj_to_primitive()
        self.assertIn('magnum_object.changes', primitive)
        obj2 = MyObj.obj_from_primitive(primitive)
        self.assertEqual(set(['foo']), obj2.obj_what_changed())
        obj2.obj_reset_changes()
        self.assertEqual(set(), obj2.obj_what_changed())

    def test_unknown_objtype(self):
        self.assertRaises(object_exception.UnsupportedObjectError,
                          base.MagnumObject.obj_class_from_name, 'foo', '1.0')

    def test_with_alternate_context(self):
        context1 = magnum_context.RequestContext('foo', 'foo')
        context2 = magnum_context.RequestContext('bar', project_id='alternate')
        obj = MyObj.query(context1)
        obj.update_test(context2)
        self.assertEqual('alternate-context', obj.bar)

    def test_orphaned_object(self):
        obj = MyObj.query(self.context)
        obj._context = None
        self.assertRaises(object_exception.OrphanedObjectError,
                          obj.update_test)

    def test_changed_1(self):
        obj = MyObj.query(self.context)
        obj.foo = 123
        self.assertEqual(set(['foo']), obj.obj_what_changed())
        obj.update_test(self.context)
        self.assertEqual(set(['foo', 'bar']), obj.obj_what_changed())
        self.assertEqual(123, obj.foo)

    def test_changed_2(self):
        obj = MyObj.query(self.context)
        obj.foo = 123
        self.assertEqual(set(['foo']), obj.obj_what_changed())
        obj.save(self.context)
        self.assertEqual(set([]), obj.obj_what_changed())
        self.assertEqual(123, obj.foo)

    def test_changed_3(self):
        obj = MyObj.query(self.context)
        obj.foo = 123
        self.assertEqual(set(['foo']), obj.obj_what_changed())
        obj.refresh(self.context)
        self.assertEqual(set([]), obj.obj_what_changed())
        self.assertEqual(321, obj.foo)
        self.assertEqual('refreshed', obj.bar)

    def test_changed_4(self):
        obj = MyObj.query(self.context)
        obj.bar = 'something'
        self.assertEqual(set(['bar']), obj.obj_what_changed())
        obj.modify_save_modify(self.context)
        self.assertEqual(set(['foo']), obj.obj_what_changed())
        self.assertEqual(42, obj.foo)
        self.assertEqual('meow', obj.bar)

    def test_static_result(self):
        obj = MyObj.query(self.context)
        self.assertEqual('bar', obj.bar)
        result = obj.marco(self.context)
        self.assertEqual('polo', result)

    def test_updates(self):
        obj = MyObj.query(self.context)
        self.assertEqual(1, obj.foo)
        obj.update_test(self.context)
        self.assertEqual('updated', obj.bar)

    def test_base_attributes(self):
        dt = datetime.datetime(1955, 11, 5)
        datatime = fields.DateTimeField()
        obj = MyObj(self.context)
        obj.created_at = dt
        obj.updated_at = dt
        expected = {'magnum_object.name': 'MyObj',
                    'magnum_object.namespace': 'magnum',
                    'magnum_object.version': '1.0',
                    'magnum_object.changes':
                        ['created_at', 'updated_at'],
                    'magnum_object.data':
                        {'created_at': datatime.stringify(dt),
                         'updated_at': datatime.stringify(dt)}
                    }
        actual = obj.obj_to_primitive()
        # magnum_object.changes is built from a set and order is undefined
        self.assertEqual(sorted(expected['magnum_object.changes']),
                         sorted(actual['magnum_object.changes']))
        del expected['magnum_object.changes'], actual['magnum_object.changes']
        self.assertEqual(expected, actual)

    def test_contains(self):
        obj = MyObj(self.context)
        self.assertNotIn('foo', obj)
        obj.foo = 1
        self.assertIn('foo', obj)
        self.assertNotIn('does_not_exist', obj)

    def test_obj_attr_is_set(self):
        obj = MyObj(self.context, foo=1)
        self.assertTrue(obj.obj_attr_is_set('foo'))
        self.assertFalse(obj.obj_attr_is_set('bar'))
        self.assertRaises(AttributeError, obj.obj_attr_is_set, 'bang')

    def test_get(self):
        obj = MyObj(self.context, foo=1)
        # Foo has value, should not get the default
        self.assertEqual(1, getattr(obj, 'foo', 2))
        # Foo has value, should return the value without error
        self.assertEqual(1, getattr(obj, 'foo'))
        # Bar without a default should lazy-load
        self.assertEqual('loaded!', getattr(obj, 'bar'))
        # Bar now has a default, but loaded value should be returned
        self.assertEqual('loaded!', getattr(obj, 'bar', 'not-loaded'))
        # Invalid attribute should raise AttributeError
        self.assertFalse(hasattr(obj, 'nothing'))

    def test_object_inheritance(self):
        base_fields = list(base.MagnumPersistentObject.fields.keys())
        myobj_fields = ['foo', 'bar', 'missing'] + base_fields
        myobj3_fields = ['new_field']
        self.assertTrue(issubclass(TestSubclassedObject, MyObj))
        self.assertEqual(len(MyObj.fields), len(myobj_fields))
        self.assertEqual(set(MyObj.fields.keys()), set(myobj_fields))
        self.assertEqual(len(TestSubclassedObject.fields),
                         len(myobj_fields) + len(myobj3_fields))
        self.assertEqual(set(TestSubclassedObject.fields.keys()),
                         set(myobj_fields) | set(myobj3_fields))

    def test_get_changes(self):
        obj = MyObj(self.context)
        self.assertEqual({}, obj.obj_get_changes())
        obj.foo = 123
        self.assertEqual({'foo': 123}, obj.obj_get_changes())
        obj.bar = 'test'
        self.assertEqual({'foo': 123, 'bar': 'test'}, obj.obj_get_changes())
        obj.obj_reset_changes()
        self.assertEqual({}, obj.obj_get_changes())

    def test_obj_fields(self):
        @base.MagnumObjectRegistry.register_if(False)
        class TestObj(base.MagnumPersistentObject, base.MagnumObject):
            fields = {'foo': fields.IntegerField()}
            obj_extra_fields = ['bar']

            @property
            def bar(self):
                return 'this is bar'

        obj = TestObj(self.context)
        self.assertEqual(set(['created_at', 'updated_at', 'foo', 'bar']),
                         set(obj.obj_fields))

    def test_obj_constructor(self):
        obj = MyObj(self.context, foo=123, bar='abc')
        self.assertEqual(123, obj.foo)
        self.assertEqual('abc', obj.bar)
        self.assertEqual(set(['foo', 'bar']), obj.obj_what_changed())


class TestObject(test_base.TestCase, _TestObject):
    pass


# This is a static dictionary that holds all fingerprints of the versioned
# objects registered with the MagnumRegistry. Each fingerprint contains
# the version of the object and an md5 hash of RPC-critical parts of the
# object (fields and remotable methods). If either the version or hash
# change, the static tree needs to be updated.
# For more information on object version testing, read
# https://docs.openstack.org/magnum/latest/contributor/objects.html
object_data = {
    'Cluster': '1.23-dfaf9ecb65a5fcab4f6c36497a8bc866',
    'ClusterTemplate': '1.20-ea3b06c5fdbf4a3fba0db9865cd2ba4c',
    'Certificate': '1.2-64f24db0e10ad4cbd72aea21d2075a80',
    'MyObj': '1.0-34c4b1aadefd177b13f9a2f894cc23cd',
    'X509KeyPair': '1.2-d81950af36c59a71365e33ce539d24f9',
    'MagnumService': '1.0-2d397ec59b0046bd5ec35cd3e06efeca',
    'Stats': '1.0-73a1cd6e3c0294c932a66547faba216c',
    'Quota': '1.0-94e100aebfa88f7d8428e007f2049c18',
    'Federation': '1.0-166da281432b083f0e4b851336e12e20',
    'NodeGroup': '1.1-70211d19fcf53903a470607f1f4a784f'
}


class TestObjectVersions(test_base.TestCase):
    def test_versions(self):
        # Test the versions of current objects with the static tree above.
        # This ensures that any incompatible object changes require a version
        # bump.
        classes = base.MagnumObjectRegistry.obj_classes()
        checker = fixture.ObjectVersionChecker(obj_classes=classes)

        expected, actual = checker.test_hashes(object_data)
        self.assertEqual(expected, actual,
                         "Fields or remotable methods in some objects have "
                         "changed. Make sure the versions of the objects has "
                         "been bumped, and update the hashes in the static "
                         "fingerprints tree (object_data). For more "
                         "information, read https://docs.openstack.org/"
                         "magnum/latest/contributor/objects.html")


class TestObjectSerializer(test_base.TestCase):

    def test_object_serialization(self):
        ser = base.MagnumObjectSerializer()
        obj = MyObj(self.context)
        primitive = ser.serialize_entity(self.context, obj)
        self.assertIn('magnum_object.name', primitive)
        obj2 = ser.deserialize_entity(self.context, primitive)
        self.assertIsInstance(obj2, MyObj)
        self.assertEqual(self.context, obj2._context)

    def test_object_serialization_iterables(self):
        ser = base.MagnumObjectSerializer()
        obj = MyObj(self.context)
        for iterable in (list, tuple, set):
            thing = iterable([obj])
            primitive = ser.serialize_entity(self.context, thing)
            self.assertEqual(1, len(primitive))
            for item in primitive:
                self.assertFalse(isinstance(item, base.MagnumObject))
            thing2 = ser.deserialize_entity(self.context, primitive)
            self.assertEqual(1, len(thing2))
            for item in thing2:
                self.assertIsInstance(item, MyObj)

    @mock.patch('magnum.objects.base.MagnumObject.indirection_api')
    def _test_deserialize_entity_newer(self, obj_version, backported_to,
                                       mock_indirection_api,
                                       my_version='1.6'):
        ser = base.MagnumObjectSerializer()
        mock_indirection_api.object_backport_versions.side_effect \
            = NotImplementedError()
        mock_indirection_api.object_backport.return_value = 'backported'

        @base.MagnumObjectRegistry.register
        class MyTestObj(MyObj):
            VERSION = my_version

        obj = MyTestObj()
        obj.VERSION = obj_version
        primitive = obj.obj_to_primitive()
        result = ser.deserialize_entity(self.context, primitive)
        if backported_to is None:
            self.assertEqual(
                False,
                mock_indirection_api.object_backport.called)
        else:
            self.assertEqual('backported', result)
            mock_indirection_api.object_backport.assert_called_with(
                self.context, primitive, backported_to)

    def test_deserialize_entity_newer_version_backports_level1(self):
        "Test object with unsupported (newer) version"
        self._test_deserialize_entity_newer('11.5', '1.6')

    def test_deserialize_entity_newer_version_backports_level2(self):
        "Test object with unsupported (newer) version"
        self._test_deserialize_entity_newer('1.25', '1.6')

    def test_deserialize_entity_same_revision_does_not_backport(self):
        "Test object with supported revision"
        self._test_deserialize_entity_newer('1.6', None)

    def test_deserialize_entity_newer_revision_does_not_backport_zero(self):
        "Test object with supported revision"
        self._test_deserialize_entity_newer('1.6.0', None)

    def test_deserialize_entity_newer_revision_does_not_backport(self):
        "Test object with supported (newer) revision"
        self._test_deserialize_entity_newer('1.6.1', None)

    def test_deserialize_entity_newer_version_passes_revision(self):
        "Test object with unsupported (newer) version and revision"
        self._test_deserialize_entity_newer('1.7', '1.6.1', my_version='1.6.1')
