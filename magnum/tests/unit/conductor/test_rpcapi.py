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
"""
Unit Tests for :py:class:`magnum.conductor.rpcapi.API`.
"""

import copy

import mock

from magnum.conductor import api as conductor_rpcapi
from magnum import objects
from magnum.tests.unit.db import base
from magnum.tests.unit.db import utils as dbutils


class RPCAPITestCase(base.DbTestCase):

    def setUp(self):
        super(RPCAPITestCase, self).setUp()
        self.fake_bay = dbutils.get_test_bay(driver='fake-driver')
        self.fake_container = dbutils.get_test_container(driver='fake-driver')
        self.fake_rc = dbutils.get_test_rc(driver='fake-driver')
        self.fake_certificate = objects.Certificate.from_db_bay(self.fake_bay)
        self.fake_certificate.csr = 'fake-csr'

    def _test_rpcapi(self, method, rpc_method, **kwargs):
        rpcapi_cls = kwargs.pop('rpcapi_cls', conductor_rpcapi.API)
        rpcapi = rpcapi_cls(topic='fake-topic')

        expected_retval = 'hello world' if rpc_method == 'call' else None

        expected_topic = 'fake-topic'
        if 'host' in kwargs:
            expected_topic += ".%s" % kwargs['host']

        target = {
            "topic": expected_topic,
            "version": kwargs.pop('version', 1.0)
        }
        expected_msg = copy.deepcopy(kwargs)

        self.fake_args = None
        self.fake_kwargs = None

        def _fake_prepare_method(*args, **kwargs):
            for kwd in kwargs:
                self.assertEqual(target[kwd], kwargs[kwd])
            return rpcapi._client

        def _fake_rpc_method(*args, **kwargs):
            self.fake_args = args
            self.fake_kwargs = kwargs
            if expected_retval:
                return expected_retval

        with mock.patch.object(rpcapi._client, "prepare") as mock_prepared:
            mock_prepared.side_effect = _fake_prepare_method

            with mock.patch.object(rpcapi._client, rpc_method) as mock_method:
                mock_method.side_effect = _fake_rpc_method
                retval = getattr(rpcapi, method)(**kwargs)
                self.assertEqual(expected_retval, retval)
                expected_args = [None, method, expected_msg]
            for arg, expected_arg in zip(self.fake_args, expected_args):
                self.assertEqual(expected_arg, arg)

    def test_bay_create(self):
        self._test_rpcapi('bay_create',
                          'call',
                          version='1.0',
                          bay=self.fake_bay,
                          bay_create_timeout=15)

    def test_bay_delete(self):
        self._test_rpcapi('bay_delete',
                          'call',
                          version='1.0',
                          uuid=self.fake_bay['uuid'])

        self._test_rpcapi('bay_delete',
                          'call',
                          version='1.1',
                          uuid=self.fake_bay['name'])

    def test_bay_update(self):
        self._test_rpcapi('bay_update',
                          'call',
                          version='1.1',
                          bay=self.fake_bay['name'])

    def test_rc_create(self):
        self._test_rpcapi('rc_create',
                          'call',
                          version='1.0',
                          rc=self.fake_rc)

    def test_rc_update(self):
        self._test_rpcapi('rc_update',
                          'call',
                          version='1.0',
                          rc_ident=self.fake_rc['uuid'],
                          bay_ident=self.fake_rc['bay_uuid'],
                          manifest={})

    def test_rc_delete(self):
        self._test_rpcapi('rc_delete',
                          'call',
                          version='1.0',
                          rc_ident=self.fake_rc['uuid'],
                          bay_ident=self.fake_rc['bay_uuid'])

        self._test_rpcapi('rc_delete',
                          'call',
                          version='1.1',
                          rc_ident=self.fake_rc['uuid'],
                          bay_ident=self.fake_rc['bay_uuid'])

    def test_container_create(self):
        self._test_rpcapi('container_create',
                          'call',
                          version='1.0',
                          container=self.fake_container)

    def test_container_delete(self):
        self._test_rpcapi('container_delete',
                          'call',
                          version='1.0',
                          container_uuid=self.fake_container['uuid'])

    def test_container_show(self):
        self._test_rpcapi('container_show',
                          'call',
                          version='1.0',
                          container_uuid=self.fake_container['uuid'])

    def test_container_reboot(self):
        self._test_rpcapi('container_reboot',
                          'call',
                          version='1.0',
                          container_uuid=self.fake_container['uuid'])

    def test_container_stop(self):
        self._test_rpcapi('container_stop',
                          'call',
                          version='1.0',
                          container_uuid=self.fake_container['uuid'])

    def test_container_start(self):
        self._test_rpcapi('container_start',
                          'call',
                          version='1.0',
                          container_uuid=self.fake_container['uuid'])

    def test_container_pause(self):
        self._test_rpcapi('container_pause',
                          'call',
                          version='1.0',
                          container_uuid=self.fake_container['uuid'])

    def test_container_unpause(self):
        self._test_rpcapi('container_unpause',
                          'call',
                          version='1.0',
                          container_uuid=self.fake_container['uuid'])

    def test_container_logs(self):
        self._test_rpcapi('container_logs',
                          'call',
                          version='1.0',
                          container_uuid=self.fake_container['uuid'])

    def test_container_exec(self):
        self._test_rpcapi('container_exec',
                          'call',
                          version='1.0',
                          container_uuid=self.fake_container['uuid'],
                          command=self.fake_container['command'])

    def test_ping_conductor(self):
        self._test_rpcapi('ping_conductor',
                          'call',
                          rpcapi_cls=conductor_rpcapi.ListenerAPI,
                          version='1.0')

    def test_sign_certificate(self):
        self._test_rpcapi('sign_certificate',
                          'call',
                          version='1.0',
                          bay=self.fake_bay,
                          certificate=self.fake_certificate)

    def test_get_ca_certificate(self):
        self._test_rpcapi('get_ca_certificate',
                          'call',
                          version='1.0',
                          bay=self.fake_bay)
