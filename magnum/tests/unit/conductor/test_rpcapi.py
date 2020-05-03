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
from unittest import mock


from magnum.conductor import api as conductor_rpcapi
from magnum import objects
from magnum.objects.fields import ClusterHealthStatus
from magnum.tests.unit.db import base
from magnum.tests.unit.db import utils as dbutils


class RPCAPITestCase(base.DbTestCase):

    def setUp(self):
        super(RPCAPITestCase, self).setUp()
        self.fake_cluster = dbutils.get_test_cluster(driver='fake-driver')
        self.fake_nodegroups = dbutils.get_nodegroups_for_cluster()
        self.fake_certificate = objects.Certificate.from_db_cluster(
            self.fake_cluster)
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

    def test_cluster_create(self):
        self._test_rpcapi('cluster_create',
                          'call',
                          version='1.0',
                          cluster=self.fake_cluster,
                          master_count=3,
                          node_count=4,
                          create_timeout=15)

    def test_cluster_delete(self):
        self._test_rpcapi('cluster_delete',
                          'call',
                          version='1.0',
                          uuid=self.fake_cluster['uuid'])

        self._test_rpcapi('cluster_delete',
                          'call',
                          version='1.1',
                          uuid=self.fake_cluster['name'])

    def test_cluster_update(self):
        self._test_rpcapi('cluster_update',
                          'call',
                          version='1.1',
                          cluster=self.fake_cluster['name'],
                          node_count=2,
                          health_status=ClusterHealthStatus.UNKNOWN,
                          health_status_reason={})

    def test_ping_conductor(self):
        self._test_rpcapi('ping_conductor',
                          'call',
                          rpcapi_cls=conductor_rpcapi.ListenerAPI,
                          version='1.0')

    def test_sign_certificate(self):
        self._test_rpcapi('sign_certificate',
                          'call',
                          version='1.0',
                          cluster=self.fake_cluster,
                          certificate=self.fake_certificate)

    def test_get_ca_certificate(self):
        self._test_rpcapi('get_ca_certificate',
                          'call',
                          version='1.0',
                          cluster=self.fake_cluster)

    def test_nodegroup_create(self):
        self._test_rpcapi('nodegroup_create',
                          'call',
                          version='1.0',
                          cluster=self.fake_cluster,
                          nodegroup=self.fake_nodegroups['worker'])

    def test_nodegroup_update(self):
        self._test_rpcapi('nodegroup_update',
                          'call',
                          version='1.0',
                          cluster=self.fake_cluster,
                          nodegroup=self.fake_nodegroups['worker'])

    def test_nodegroup_delete(self):
        self._test_rpcapi('nodegroup_delete',
                          'call',
                          version='1.0',
                          cluster=self.fake_cluster,
                          nodegroup=self.fake_nodegroups['worker'])
