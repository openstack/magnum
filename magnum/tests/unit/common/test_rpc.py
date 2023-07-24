# Copyright 2017 OpenStack Foundation
# All Rights Reserved.
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

from unittest import mock

import oslo_messaging as messaging
from oslo_messaging.rpc import dispatcher
from oslo_serialization import jsonutils

from magnum.common import context
from magnum.common import rpc
from magnum.tests import base


class TestRpc(base.TestCase):
    @mock.patch.object(rpc, 'profiler', None)
    @mock.patch.object(rpc, 'RequestContextSerializer')
    @mock.patch.object(messaging, 'get_rpc_client')
    def test_get_client(self, mock_get, mock_ser):
        rpc.TRANSPORT = mock.Mock()
        tgt = mock.Mock()
        ser = mock.Mock()
        mock_get.return_value = 'client'
        mock_ser.return_value = ser

        client = rpc.get_client(tgt, version_cap='1.0', serializer=ser,
                                timeout=6969)

        mock_get.assert_called_once_with(rpc.TRANSPORT,
                                         tgt, version_cap='1.0',
                                         serializer=ser, timeout=6969)
        self.assertEqual('client', client)

    @mock.patch.object(rpc, 'profiler', mock.Mock())
    @mock.patch.object(rpc, 'ProfilerRequestContextSerializer')
    @mock.patch.object(messaging, 'get_rpc_client')
    def test_get_client_profiler_enabled(self, mock_get, mock_ser):
        rpc.TRANSPORT = mock.Mock()
        tgt = mock.Mock()
        ser = mock.Mock()
        mock_get.return_value = 'client'
        mock_ser.return_value = ser

        client = rpc.get_client(tgt, version_cap='1.0', serializer=ser,
                                timeout=6969)

        mock_get.assert_called_once_with(rpc.TRANSPORT,
                                         tgt, version_cap='1.0',
                                         serializer=ser, timeout=6969)
        self.assertEqual('client', client)

    @mock.patch.object(rpc, 'profiler', None)
    @mock.patch.object(rpc, 'RequestContextSerializer')
    @mock.patch.object(messaging, 'get_rpc_server')
    def test_get_server(self, mock_get, mock_ser):
        rpc.TRANSPORT = mock.Mock()
        ser = mock.Mock()
        tgt = mock.Mock()
        ends = mock.Mock()
        mock_get.return_value = 'server'
        mock_ser.return_value = ser
        access_policy = dispatcher.DefaultRPCAccessPolicy
        server = rpc.get_server(tgt, ends, serializer=ser)

        mock_get.assert_called_once_with(rpc.TRANSPORT, tgt, ends,
                                         executor='eventlet', serializer=ser,
                                         access_policy=access_policy)
        self.assertEqual('server', server)

    @mock.patch.object(rpc, 'profiler', mock.Mock())
    @mock.patch.object(rpc, 'ProfilerRequestContextSerializer')
    @mock.patch.object(messaging, 'get_rpc_server')
    def test_get_server_profiler_enabled(self, mock_get, mock_ser):
        rpc.TRANSPORT = mock.Mock()
        ser = mock.Mock()
        tgt = mock.Mock()
        ends = mock.Mock()
        mock_ser.return_value = ser
        mock_get.return_value = 'server'
        access_policy = dispatcher.DefaultRPCAccessPolicy
        server = rpc.get_server(tgt, ends, serializer='foo')

        mock_ser.assert_called_once_with('foo')
        mock_get.assert_called_once_with(rpc.TRANSPORT, tgt, ends,
                                         executor='eventlet', serializer=ser,
                                         access_policy=access_policy)
        self.assertEqual('server', server)

    @mock.patch.object(messaging, 'TransportURL')
    def test_get_transport_url(self, mock_url):
        conf = mock.Mock()
        rpc.CONF = conf
        mock_url.parse.return_value = 'foo'

        url = rpc.get_transport_url(url_str='bar')

        self.assertEqual('foo', url)
        mock_url.parse.assert_called_once_with(conf, 'bar')

    @mock.patch.object(messaging, 'TransportURL')
    def test_get_transport_url_null(self, mock_url):
        conf = mock.Mock()
        rpc.CONF = conf
        mock_url.parse.return_value = 'foo'

        url = rpc.get_transport_url()

        self.assertEqual('foo', url)
        mock_url.parse.assert_called_once_with(conf, None)

    def test_cleanup_transport_null(self):
        rpc.TRANSPORT = None
        rpc.NOTIFIER = mock.Mock()
        self.assertRaises(AssertionError, rpc.cleanup)

    def test_cleanup_notifier_null(self):
        rpc.TRANSPORT = mock.Mock()
        rpc.NOTIFIER = None
        self.assertRaises(AssertionError, rpc.cleanup)

    def test_cleanup(self):
        rpc.NOTIFIER = mock.Mock()
        rpc.TRANSPORT = mock.Mock()
        trans_cleanup = mock.Mock()
        rpc.TRANSPORT.cleanup = trans_cleanup

        rpc.cleanup()

        trans_cleanup.assert_called_once_with()
        self.assertIsNone(rpc.TRANSPORT)
        self.assertIsNone(rpc.NOTIFIER)

    def test_add_extra_exmods(self):
        rpc.EXTRA_EXMODS = []

        rpc.add_extra_exmods('foo', 'bar')

        self.assertEqual(['foo', 'bar'], rpc.EXTRA_EXMODS)

    def test_clear_extra_exmods(self):
        rpc.EXTRA_EXMODS = ['foo', 'bar']

        rpc.clear_extra_exmods()

        self.assertEqual(0, len(rpc.EXTRA_EXMODS))

    def test_serialize_entity(self):
        with mock.patch.object(jsonutils, 'to_primitive') as mock_prim:
            rpc.JsonPayloadSerializer.serialize_entity('context', 'entity')

        mock_prim.assert_called_once_with('entity', convert_instances=True)


class TestRequestContextSerializer(base.TestCase):
    def setUp(self):
        super(TestRequestContextSerializer, self).setUp()
        self.mock_base = mock.Mock()
        self.ser = rpc.RequestContextSerializer(self.mock_base)
        self.ser_null = rpc.RequestContextSerializer(None)

    def test_serialize_entity(self):
        self.mock_base.serialize_entity.return_value = 'foo'

        ser_ent = self.ser.serialize_entity('context', 'entity')

        self.mock_base.serialize_entity.assert_called_once_with('context',
                                                                'entity')
        self.assertEqual('foo', ser_ent)

    def test_serialize_entity_null_base(self):
        ser_ent = self.ser_null.serialize_entity('context', 'entity')

        self.assertEqual('entity', ser_ent)

    def test_deserialize_entity(self):
        self.mock_base.deserialize_entity.return_value = 'foo'

        deser_ent = self.ser.deserialize_entity('context', 'entity')

        self.mock_base.deserialize_entity.assert_called_once_with('context',
                                                                  'entity')
        self.assertEqual('foo', deser_ent)

    def test_deserialize_entity_null_base(self):
        deser_ent = self.ser_null.deserialize_entity('context', 'entity')

        self.assertEqual('entity', deser_ent)

    def test_serialize_context(self):
        context = mock.Mock()

        self.ser.serialize_context(context)

        context.to_dict.assert_called_once_with()

    @mock.patch.object(context, 'RequestContext')
    def test_deserialize_context(self, mock_req):
        self.ser.deserialize_context('context')

        mock_req.from_dict.assert_called_once_with('context')


class TestProfilerRequestContextSerializer(base.TestCase):
    def setUp(self):
        super(TestProfilerRequestContextSerializer, self).setUp()
        self.ser = rpc.ProfilerRequestContextSerializer(mock.Mock())

    @mock.patch('magnum.common.rpc.profiler')
    def test_serialize_context(self, mock_profiler):
        prof = mock_profiler.get.return_value
        prof.hmac_key = 'swordfish'
        prof.get_base_id.return_value = 'baseid'
        prof.get_id.return_value = 'parentid'

        context = mock.Mock()
        context.to_dict.return_value = {'project_id': 'test'}

        self.assertEqual({
            'project_id': 'test',
            'trace_info': {
                'hmac_key': 'swordfish',
                'base_id': 'baseid',
                'parent_id': 'parentid'
            }
        }, self.ser.serialize_context(context))

    @mock.patch('magnum.common.rpc.profiler')
    def test_deserialize_context(self, mock_profiler):
        serialized = {'project_id': 'test',
                      'trace_info': {
                          'hmac_key': 'swordfish',
                          'base_id': 'baseid',
                          'parent_id': 'parentid'}}

        context = self.ser.deserialize_context(serialized)

        self.assertEqual('test', context.project_id)
        mock_profiler.init.assert_called_once_with(
            hmac_key='swordfish', base_id='baseid', parent_id='parentid')
