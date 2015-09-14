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

import iso8601
import mock
import netaddr
from oslo_utils import timeutils
from oslo_versionedobjects import fields
from oslo_versionedobjects import fixture

from magnum.common import context as magnum_context
from magnum.common import exception
from magnum.objects import base
from magnum.objects import utils
from magnum.tests import base as test_base

gettext.install('magnum')


@base.MagnumObjectRegistry.register
class MyObj(base.MagnumObject):
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
        self.save()
        self.foo = 42


class MyObj2(object):
    @classmethod
    def obj_name(cls):
        return 'MyObj'

    @base.remotable_classmethod
    def get(cls, *args, **kwargs):
        pass


class TestSubclassedObject(MyObj):
    fields = {'new_field': fields.StringField()}


class TestUtils(test_base.TestCase):

    def test_datetime_or_none(self):
        naive_dt = datetime.datetime.now()
        dt = timeutils.parse_isotime(timeutils.isotime(naive_dt))
        self.assertEqual(utils.datetime_or_none(dt), dt)
        self.assertEqual(utils.datetime_or_none(dt),
                         naive_dt.replace(tzinfo=iso8601.iso8601.Utc(),
                                          microsecond=0))
        self.assertIsNone(utils.datetime_or_none(None))
        self.assertRaises(ValueError, utils.datetime_or_none, 'foo')

    def test_datetime_or_str_or_none(self):
        dts = timeutils.isotime()
        dt = timeutils.parse_isotime(dts)
        self.assertEqual(utils.datetime_or_str_or_none(dt), dt)
        self.assertIsNone(utils.datetime_or_str_or_none(None))
        self.assertEqual(utils.datetime_or_str_or_none(dts), dt)
        self.assertRaises(ValueError, utils.datetime_or_str_or_none, 'foo')

    def test_int_or_none(self):
        self.assertEqual(utils.int_or_none(1), 1)
        self.assertEqual(utils.int_or_none('1'), 1)
        self.assertIsNone(utils.int_or_none(None))
        self.assertRaises(ValueError, utils.int_or_none, 'foo')

    def test_str_or_none(self):
        class Obj(object):
            pass
        self.assertEqual(utils.str_or_none('foo'), 'foo')
        self.assertEqual(utils.str_or_none(1), '1')
        self.assertIsNone(utils.str_or_none(None))

    def test_ip_or_none(self):
        ip4 = netaddr.IPAddress('1.2.3.4', 4)
        ip6 = netaddr.IPAddress('1::2', 6)
        self.assertEqual(utils.ip_or_none(4)('1.2.3.4'), ip4)
        self.assertEqual(utils.ip_or_none(6)('1::2'), ip6)
        self.assertIsNone(utils.ip_or_none(4)(None))
        self.assertIsNone(utils.ip_or_none(6)(None))
        self.assertRaises(netaddr.AddrFormatError, utils.ip_or_none(4), 'foo')
        self.assertRaises(netaddr.AddrFormatError, utils.ip_or_none(6), 'foo')

    def test_dt_serializer(self):
        class Obj(object):
            foo = utils.dt_serializer('bar')

        obj = Obj()
        obj.bar = timeutils.parse_isotime('1955-11-05T00:00:00Z')
        self.assertEqual('1955-11-05T00:00:00Z', obj.foo())
        obj.bar = None
        self.assertIsNone(obj.foo())
        obj.bar = 'foo'
        self.assertRaises(AttributeError, obj.foo)

    def test_dt_deserializer(self):
        dt = timeutils.parse_isotime('1955-11-05T00:00:00Z')
        self.assertEqual(utils.dt_deserializer(None, timeutils.isotime(dt)),
                         dt)
        self.assertIsNone(utils.dt_deserializer(None, None))
        self.assertRaises(ValueError, utils.dt_deserializer, None, 'foo')


class _TestObject(object):
    def test_hydration_type_error(self):
        primitive = {'magnum_object.name': 'MyObj',
                     'magnum_object.namespace': 'magnum',
                     'magnum_object.version': '1.5',
                     'magnum_object.data': {'foo': 'a'}}
        self.assertRaises(ValueError, MyObj.obj_from_primitive, primitive)

    def test_hydration(self):
        primitive = {'magnum_object.name': 'MyObj',
                     'magnum_object.namespace': 'magnum',
                     'magnum_object.version': '1.5',
                     'magnum_object.data': {'foo': 1}}
        obj = MyObj.obj_from_primitive(primitive)
        self.assertEqual(1, obj.foo)

    def test_hydration_bad_ns(self):
        primitive = {'magnum_object.name': 'MyObj',
                     'magnum_object.namespace': 'foo',
                     'magnum_object.version': '1.5',
                     'magnum_object.data': {'foo': 1}}
        self.assertRaises(exception.UnsupportedObjectError,
                          MyObj.obj_from_primitive, primitive)

    def test_dehydration(self):
        expected = {'magnum_object.name': 'MyObj',
                    'magnum_object.namespace': 'magnum',
                    'magnum_object.version': '1.5',
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
        class Foo(base.MagnumObject):
            fields = {'foobar': fields.IntegerField()}
        obj = Foo(self.context)
        # NOTE(danms): Can't use assertRaisesRegexp() because of py26
        raised = False
        try:
            obj.foobar
        except NotImplementedError as ex:
            raised = True
        self.assertTrue(raised)
        self.assertTrue('foobar' in str(ex))

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
        self.assertTrue('magnum_object.changes' in primitive)
        obj2 = MyObj.obj_from_primitive(primitive)
        self.assertEqual(set(['foo']), obj2.obj_what_changed())
        obj2.obj_reset_changes()
        self.assertEqual(set(), obj2.obj_what_changed())

    def test_unknown_objtype(self):
        self.assertRaises(exception.UnsupportedObjectError,
                          base.MagnumObject.obj_class_from_name, 'foo', '1.0')

    def test_with_alternate_context(self):
        context1 = magnum_context.RequestContext('foo', 'foo')
        context2 = magnum_context.RequestContext('bar', project_id='alternate')
        obj = MyObj.query(context1)
        obj.update_test(context2)
        self.assertEqual('alternate-context', obj.bar)
        self.assertRemotes()

    def test_orphaned_object(self):
        obj = MyObj.query(self.context)
        obj._context = None
        self.assertRaises(exception.OrphanedObjectError,
                          obj.update_test)
        self.assertRemotes()

    def test_changed_1(self):
        obj = MyObj.query(self.context)
        obj.foo = 123
        self.assertEqual(set(['foo']), obj.obj_what_changed())
        obj.update_test(self.context)
        self.assertEqual(set(['foo', 'bar']), obj.obj_what_changed())
        self.assertEqual(123, obj.foo)
        self.assertRemotes()

    def test_changed_2(self):
        obj = MyObj.query(self.context)
        obj.foo = 123
        self.assertEqual(set(['foo']), obj.obj_what_changed())
        obj.save()
        self.assertEqual(set([]), obj.obj_what_changed())
        self.assertEqual(123, obj.foo)
        self.assertRemotes()

    def test_changed_3(self):
        obj = MyObj.query(self.context)
        obj.foo = 123
        self.assertEqual(set(['foo']), obj.obj_what_changed())
        obj.refresh()
        self.assertEqual(set([]), obj.obj_what_changed())
        self.assertEqual(321, obj.foo)
        self.assertEqual('refreshed', obj.bar)
        self.assertRemotes()

    def test_changed_4(self):
        obj = MyObj.query(self.context)
        obj.bar = 'something'
        self.assertEqual(set(['bar']), obj.obj_what_changed())
        obj.modify_save_modify(self.context)
        self.assertEqual(set(['foo']), obj.obj_what_changed())
        self.assertEqual(42, obj.foo)
        self.assertEqual('meow', obj.bar)
        self.assertRemotes()

    def test_static_result(self):
        obj = MyObj.query(self.context)
        self.assertEqual('bar', obj.bar)
        result = obj.marco()
        self.assertEqual('polo', result)
        self.assertRemotes()

    def test_updates(self):
        obj = MyObj.query(self.context)
        self.assertEqual(1, obj.foo)
        obj.update_test()
        self.assertEqual('updated', obj.bar)
        self.assertRemotes()

    def test_base_attributes(self):
        dt = datetime.datetime(1955, 11, 5)
        obj = MyObj(self.context)
        obj.created_at = dt
        obj.updated_at = dt
        expected = {'magnum_object.name': 'MyObj',
                    'magnum_object.namespace': 'magnum',
                    'magnum_object.version': '1.0',
                    'magnum_object.changes':
                        ['created_at', 'updated_at'],
                    'magnum_object.data':
                        {'created_at': timeutils.isotime(dt),
                         'updated_at': timeutils.isotime(dt)}
                    }
        actual = obj.obj_to_primitive()
        # magnum_object.changes is built from a set and order is undefined
        self.assertEqual(sorted(expected['magnum_object.changes']),
                         sorted(actual['magnum_object.changes']))
        del expected['magnum_object.changes'], actual['magnum_object.changes']
        self.assertEqual(expected, actual)

    def test_contains(self):
        obj = MyObj(self.context)
        self.assertFalse('foo' in obj)
        obj.foo = 1
        self.assertTrue('foo' in obj)
        self.assertFalse('does_not_exist' in obj)

    def test_obj_attr_is_set(self):
        obj = MyObj(self.context, foo=1)
        self.assertTrue(obj.obj_attr_is_set('foo'))
        self.assertFalse(obj.obj_attr_is_set('bar'))
        self.assertRaises(AttributeError, obj.obj_attr_is_set, 'bang')

    def test_get(self):
        obj = MyObj(self.context, foo=1)
        # Foo has value, should not get the default
        self.assertEqual(obj.get('foo', 2), 1)
        # Foo has value, should return the value without error
        self.assertEqual(obj.get('foo'), 1)
        # Bar is not loaded, so we should get the default
        self.assertEqual(obj.get('bar', 'not-loaded'), 'not-loaded')
        # Bar without a default should lazy-load
        self.assertEqual(obj.get('bar'), 'loaded!')
        # Bar now has a default, but loaded value should be returned
        self.assertEqual(obj.get('bar', 'not-loaded'), 'loaded!')
        # Invalid attribute should raise AttributeError
        self.assertRaises(AttributeError, obj.get, 'nothing')
        # ...even with a default
        self.assertRaises(AttributeError, obj.get, 'nothing', 3)

    def test_object_inheritance(self):
        base_fields = list(base.MagnumObject.fields.keys())
        myobj_fields = ['foo', 'bar', 'missing'] + base_fields
        myobj3_fields = ['new_field']
        self.assertTrue(issubclass(TestSubclassedObject, MyObj))
        self.assertEqual(len(myobj_fields), len(MyObj.fields))
        self.assertEqual(set(myobj_fields), set(MyObj.fields.keys()))
        self.assertEqual(len(myobj_fields) + len(myobj3_fields),
                         len(TestSubclassedObject.fields))
        self.assertEqual(set(myobj_fields) | set(myobj3_fields),
                         set(TestSubclassedObject.fields.keys()))

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
        class TestObj(base.MagnumObject):
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


# This is a static dictionary that holds all fingerprints of the versioned
# objects registered with the MagnumRegistry. Each fingerprint contains
# the version of the object and an md5 hash of RPC-critical parts of the
# object (fields and remotable methods). If either the version or hash
# change, the static tree needs to be updated.
# For more information on object version testing, read
# http://docs.openstack.org/developer/magnum/objects.html
object_data = {
    'Bay': '1.0-35edde13ad178e9419e7ea8b6d580bcd',
    'BayLock': '1.0-7d1eb08cf2070523bd210369c7a2e076',
    'BayModel': '1.0-06863f04ab4b98307e3d1b736d3137bf',
    'Certificate': '1.0-2aff667971b85c1edf8d15684fd7d5e2',
    'Container': '1.0-e12affbba5f8a748882a3ae98aced282',
    'MyObj': '1.0-b43567e512438205e32f4e95ca616697',
    'Node': '1.0-30943e6e3387a2fae7490b57c4239a17',
    'Pod': '1.0-69b579203c6d726be7878c606626e438',
    'ReplicationController': '1.0-782b7deb9307b2807101541b7e58b8a2',
    'Service': '1.0-d4b8c0f3a234aec35d273196e18f7ed1',
    'X509KeyPair': '1.0-fd008eba0fbc390e0e5da247bba4eedd',
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
                         "fingerprints tree (object_data).")


class TestObjectSerializer(test_base.TestCase):

    def test_object_serialization(self):
        ser = base.MagnumObjectSerializer()
        obj = MyObj(self.context)
        primitive = ser.serialize_entity(self.context, obj)
        self.assertTrue('magnum_object.name' in primitive)
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
            self.assertFalse(mock_indirection_api.object_backport.called)
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
