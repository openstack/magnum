# Copyright 2014
# The Cloudscaling Group, Inc.
#
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

import json

import mock
from oslo_config import cfg
import oslo_messaging as messaging

from magnum.api.controllers import root
from magnum.api import hooks
from magnum.common import context as magnum_context
from magnum.tests.api import base as api_base
from magnum.tests import base
from magnum.tests import fakes


class TestContextHook(base.BaseTestCase):

    def setUp(self):
        super(TestContextHook, self).setUp()
        self.app = fakes.FakeApp()

    def test_context_hook_before_method(self):
        state = mock.Mock(request=fakes.FakePecanRequest())
        hook = hooks.ContextHook()
        hook.before(state)
        ctx = state.request.context
        self.assertIsInstance(ctx, magnum_context.RequestContext)
        self.assertEqual(ctx.auth_token,
                         fakes.fakeAuthTokenHeaders['X-Auth-Token'])
        self.assertEqual(ctx.project_id,
                         fakes.fakeAuthTokenHeaders['X-Project-Id'])
        self.assertEqual(ctx.user_id,
                         fakes.fakeAuthTokenHeaders['X-User-Id'])
        self.assertEqual(ctx.auth_url,
                         fakes.fakeAuthTokenHeaders['X-Auth-Url'])
        self.assertEqual(ctx.domain_name,
                         fakes.fakeAuthTokenHeaders['X-User-Domain-Name'])
        self.assertEqual(ctx.domain_id,
                         fakes.fakeAuthTokenHeaders['X-User-Domain-Id'])
        self.assertIsNone(ctx.auth_token_info)

    def test_context_hook_before_method_auth_info(self):
        state = mock.Mock(request=fakes.FakePecanRequest())
        state.request.environ['keystone.token_info'] = 'assert_this'
        hook = hooks.ContextHook()
        hook.before(state)
        ctx = state.request.context
        self.assertIsInstance(ctx, magnum_context.RequestContext)
        self.assertEqual(fakes.fakeAuthTokenHeaders['X-Auth-Token'],
                         ctx.auth_token)
        self.assertEqual('assert_this', ctx.auth_token_info)


class TestNoExceptionTracebackHook(api_base.FunctionalTest):

    TRACE = [u'Traceback (most recent call last):',
             u'  File "/opt/stack/magnum/magnum/openstack/common/rpc/amqp.py",'
             ' line 434, in _process_data\\n   **args)',
             u'  File "/opt/stack/magnum/magnum/openstack/common/rpc/'
             'dispatcher.py", line 172, in dispatch\\n   result ='
             ' getattr(proxyobj, method)(context, **kwargs)']
    MSG_WITHOUT_TRACE = "Test exception message."
    MSG_WITH_TRACE = MSG_WITHOUT_TRACE + "\n" + "\n".join(TRACE)

    def setUp(self):
        super(TestNoExceptionTracebackHook, self).setUp()
        p = mock.patch.object(root.Root, 'convert')
        self.root_convert_mock = p.start()
        self.addCleanup(p.stop)

    def test_hook_exception_success(self):
        self.root_convert_mock.side_effect = Exception(self.MSG_WITH_TRACE)

        response = self.get_json('/', path_prefix='', expect_errors=True)

        actual_msg = json.loads(response.json['error_message'])['faultstring']
        self.assertEqual(self.MSG_WITHOUT_TRACE, actual_msg)

    def test_hook_remote_error_success(self):
        test_exc_type = 'TestException'
        self.root_convert_mock.side_effect = messaging.rpc.RemoteError(
            test_exc_type, self.MSG_WITHOUT_TRACE, self.TRACE)

        response = self.get_json('/', path_prefix='', expect_errors=True)

        # NOTE(max_lobur): For RemoteError the client message will still have
        # some garbage because in RemoteError traceback is serialized as a list
        # instead of'\n'.join(trace). But since RemoteError is kind of very
        # rare thing (happens due to wrong deserialization settings etc.)
        # we don't care about this garbage.
        expected_msg = ("Remote error: %s %s"
                        % (test_exc_type, self.MSG_WITHOUT_TRACE) + "\n[u'")
        actual_msg = json.loads(response.json['error_message'])['faultstring']
        self.assertEqual(expected_msg, actual_msg)

    def test_hook_without_traceback(self):
        msg = "Error message without traceback \n but \n multiline"
        self.root_convert_mock.side_effect = Exception(msg)

        response = self.get_json('/', path_prefix='', expect_errors=True)

        actual_msg = json.loads(response.json['error_message'])['faultstring']
        self.assertEqual(msg, actual_msg)

    def test_hook_server_debug_on_serverfault(self):
        cfg.CONF.set_override('debug', True)
        self.root_convert_mock.side_effect = Exception(self.MSG_WITH_TRACE)

        response = self.get_json('/', path_prefix='', expect_errors=True)

        actual_msg = json.loads(
            response.json['error_message'])['faultstring']
        self.assertEqual(self.MSG_WITHOUT_TRACE, actual_msg)

    def test_hook_server_debug_on_clientfault(self):
        cfg.CONF.set_override('debug', True)
        client_error = Exception(self.MSG_WITH_TRACE)
        client_error.code = 400
        self.root_convert_mock.side_effect = client_error

        response = self.get_json('/', path_prefix='', expect_errors=True)

        actual_msg = json.loads(
            response.json['error_message'])['faultstring']
        self.assertEqual(self.MSG_WITH_TRACE, actual_msg)
