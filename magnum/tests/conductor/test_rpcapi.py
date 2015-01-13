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
from magnum.tests.db import base
from magnum.tests.db import utils as dbutils


class RPCAPITestCase(base.DbTestCase):

    def setUp(self):
        super(RPCAPITestCase, self).setUp()
        self.fake_bay = dbutils.get_test_bay(driver='fake-driver')
        self.fake_pod = dbutils.get_test_pod(driver='fake-driver')
        self.fake_rc = dbutils.get_test_rc(driver='fake-driver')
        self.fake_service = dbutils.get_test_service(driver='fake-driver')

    def _test_rpcapi(self, method, rpc_method, **kwargs):
        rpcapi = conductor_rpcapi.API(topic='fake-topic')

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
                self.assertEqual(kwargs[kwd], target[kwd])
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
                self.assertEqual(retval, expected_retval)
                expected_args = [None, method, expected_msg]
            for arg, expected_arg in zip(self.fake_args, expected_args):
                self.assertEqual(arg, expected_arg)

    def test_bay_create(self):
        self._test_rpcapi('bay_create',
                          'call',
                          version='1.0',
                          bay=self.fake_bay)

    def test_bay_delete(self):
        self._test_rpcapi('bay_delete',
                          'call',
                          version='1.0',
                          uuid=self.fake_bay['uuid'])

    def test_service_create(self):
        self._test_rpcapi('service_create',
                          'call',
                          version='1.0',
                          service=self.fake_service)

    # TODO(sdake) the parameters to delete operations are highly suspect
    def test_service_delete(self):
        self._test_rpcapi('service_delete',
                          'call',
                          version='1.0',
                          service=self.fake_service)

    def test_pod_create(self):
        self._test_rpcapi('pod_create',
                          'call',
                          version='1.0',
                          pod=self.fake_pod)

    def test_pod_delete(self):
        self._test_rpcapi('pod_delete',
                          'call',
                          version='1.0',
                          uuid=self.fake_pod['uuid'])

    def test_rc_create(self):
        self._test_rpcapi('rc_create',
                          'call',
                          version='1.0',
                          rc=self.fake_rc)

    # TODO(sdake) the parameters to delete operations are highly suspect
    def test_rc_delete(self):
        self._test_rpcapi('rc_delete',
                          'call',
                          version='1.0',
                          rc=self.fake_rc)
