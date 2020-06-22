# Copyright 2015 Huawei Technologies Co.,LTD.
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

from unittest import mock
from unittest.mock import patch

from magnum.conductor import utils
from magnum import objects
from magnum.tests import base


class TestConductorUtils(base.TestCase):

    def _test_retrieve_cluster(self, expected_cluster_uuid,
                               mock_cluster_get_by_uuid):
        expected_context = 'context'
        utils.retrieve_cluster(expected_context, expected_cluster_uuid)
        mock_cluster_get_by_uuid.assert_called_once_with(
            expected_context, expected_cluster_uuid)

    def get_fake_id(self):
        return '5d12f6fd-a196-4bf0-ae4c-1f639a523a52'

    def _get_type_uri(self):
        return 'service/security/account/user'

    @patch('magnum.objects.ClusterTemplate.get_by_uuid')
    def test_retrieve_cluster_template(self,
                                       mock_cluster_template_get_by_uuid):
        expected_context = 'context'
        expected_cluster_template_uuid = 'ClusterTemplate_uuid'

        cluster = objects.Cluster({})
        cluster.cluster_template_id = expected_cluster_template_uuid

        utils.retrieve_cluster_template(expected_context, cluster)

        mock_cluster_template_get_by_uuid.assert_called_once_with(
            expected_context,
            expected_cluster_template_uuid)

    @patch('oslo_utils.uuidutils.is_uuid_like')
    @patch('magnum.objects.Cluster.get_by_name')
    def test_retrieve_cluster_uuid_from_name(self, mock_cluster_get_by_name,
                                             mock_uuid_like):
        cluster = objects.Cluster(uuid='5d12f6fd-a196-4bf0-ae4c-1f639a523a52')
        mock_uuid_like.return_value = False
        mock_cluster_get_by_name.return_value = cluster
        cluster_uuid = utils.retrieve_cluster_uuid('context', 'fake_name')
        self.assertEqual('5d12f6fd-a196-4bf0-ae4c-1f639a523a52', cluster_uuid)

        mock_uuid_like.assert_called_once_with('fake_name')
        mock_cluster_get_by_name.assert_called_once_with('context',
                                                         'fake_name')

    @patch('oslo_utils.uuidutils.is_uuid_like')
    @patch('magnum.objects.Cluster.get_by_name')
    def test_retrieve_cluster_uuid_from_uuid(self, mock_cluster_get_by_name,
                                             mock_uuid_like):
        cluster_uuid = utils.retrieve_cluster_uuid(
            'context',
            '5d12f6fd-a196-4bf0-ae4c-1f639a523a52')
        self.assertEqual('5d12f6fd-a196-4bf0-ae4c-1f639a523a52', cluster_uuid)
        mock_uuid_like.return_value = True
        mock_cluster_get_by_name.assert_not_called()

    def _get_heat_stacks_get_mock_obj(self, status):
        mock_stack = mock.MagicMock()
        mock_osc = mock.MagicMock()
        mock_stack_obj = mock.MagicMock()
        mock_stack_obj.stack_status = status
        stack_get = mock.MagicMock()
        stack_get.get.return_value = mock_stack_obj
        mock_stack.stacks = stack_get
        mock_osc.heat.return_value = mock_stack
        return mock_osc

    @patch('magnum.conductor.utils.retrieve_cluster')
    @patch('magnum.conductor.utils.clients.OpenStackClients')
    def test_object_has_stack_invalid_status(self, mock_oscs,
                                             mock_retrieve_cluster):

        mock_osc = self._get_heat_stacks_get_mock_obj("INVALID_STATUS")
        mock_oscs.return_value = mock_osc
        self.assertTrue(utils.object_has_stack('context', self.get_fake_id()))
        mock_retrieve_cluster.assert_called_with('context', self.get_fake_id())

    @patch('magnum.conductor.utils.retrieve_cluster')
    @patch('magnum.conductor.utils.clients.OpenStackClients')
    def test_object_has_stack_delete_in_progress(self, mock_oscs,
                                                 mock_retrieve_cluster):

        mock_osc = self._get_heat_stacks_get_mock_obj("DELETE_IN_PROGRESS")
        mock_oscs.return_value = mock_osc
        self.assertFalse(utils.object_has_stack('context', self.get_fake_id()))
        mock_retrieve_cluster.assert_called_with('context', self.get_fake_id())

    @patch('magnum.conductor.utils.retrieve_cluster')
    @patch('magnum.conductor.utils.clients.OpenStackClients')
    def test_object_has_stack_delete_complete_status(self, mock_oscs,
                                                     mock_retrieve_cluster):
        mock_osc = self._get_heat_stacks_get_mock_obj("DELETE_COMPLETE")
        mock_oscs.return_value = mock_osc
        self.assertFalse(utils.object_has_stack('context', self.get_fake_id()))
        mock_retrieve_cluster.assert_called_with('context', self.get_fake_id())

    @patch('magnum.objects.Cluster.get_by_uuid')
    def test_retrieve_cluster_uuid(self, mock_get_by_uuid):
        mock_get_by_uuid.return_value = True
        utils.retrieve_cluster('context',
                               '5d12f6fd-a196-4bf0-ae4c-1f639a523a52')
        self.assertTrue(mock_get_by_uuid.called)

    @patch('magnum.objects.Cluster.get_by_name')
    def test_retrieve_cluster_name(self, mock_get_by_name):
        mock_get_by_name.return_value = mock.MagicMock()
        utils.retrieve_cluster('context', '1')
        self.assertTrue(mock_get_by_name.called)

    @patch('magnum.conductor.utils.resource.Resource')
    def test_get_request_audit_info_with_none_context(self, mock_resource):
        mock_resource.return_value = 'resource'
        result = utils._get_request_audit_info(context=None)
        self.assertTrue(mock_resource.called)
        self.assertEqual(result, 'resource')

    def _assert_for_user_project_domain_resource(self, result, ctxt, mock_res):
        mock_res.assert_called_once_with(typeURI=self._get_type_uri())
        self.assertEqual(result.user_id, ctxt.user_id)
        self.assertEqual(result.project_id, ctxt.project_id)
        self.assertEqual(result.domain_id, ctxt.domain_id)

    def _get_context(self, user_id=None, project_id=None, domain_id=None):
        context = self.mock_make_context()
        context.user_id = user_id
        context.project_id = project_id
        context.domain_id = domain_id
        return context

    @patch('magnum.conductor.utils.resource.Resource')
    def test_get_request_audit_info_with_none_userid(self, mock_resource):
        context = self._get_context(project_id='test_project_id',
                                    domain_id='test_domain_id')

        mock_resource.return_value = context
        result = utils._get_request_audit_info(context)
        self._assert_for_user_project_domain_resource(result, context,
                                                      mock_resource)

    @patch('magnum.conductor.utils.resource.Resource')
    def test_get_request_audit_info_with_none_projectid(self, mock_resource):
        context = self._get_context(user_id='test_user_id',
                                    domain_id='test_domain_id')

        mock_resource.return_value = context
        result = utils._get_request_audit_info(context)
        self._assert_for_user_project_domain_resource(result, context,
                                                      mock_resource)

    @patch('magnum.conductor.utils.resource.Resource')
    def test_get_request_audit_info_with_none_domainid(self, mock_resource):
        context = self._get_context(user_id='test_user_id',
                                    project_id='test_project_id')

        mock_resource.return_value = context
        result = utils._get_request_audit_info(context)
        self._assert_for_user_project_domain_resource(result, context,
                                                      mock_resource)

    @patch('magnum.conductor.utils.resource.Resource')
    def test_get_request_audit_info_with_none_domainid_userid(self,
                                                              mock_resource):

        context = self._get_context(project_id='test_project_id')
        mock_resource.return_value = context
        result = utils._get_request_audit_info(context)
        self._assert_for_user_project_domain_resource(result, context,
                                                      mock_resource)

    @patch('magnum.conductor.utils.resource.Resource')
    def test_get_request_audit_info_with_none_userid_projectid(self,
                                                               mock_resource):

        context = self._get_context(domain_id='test_domain_id')
        mock_resource.return_value = context
        result = utils._get_request_audit_info(context)
        self._assert_for_user_project_domain_resource(result, context,
                                                      mock_resource)

    @patch('magnum.conductor.utils.resource.Resource')
    def test_get_request_audit_info_with_none_domain_project_id(self,
                                                                mock_resource):

        context = self._get_context(user_id='test_user_id')
        mock_resource.return_value = context
        result = utils._get_request_audit_info(context)
        self._assert_for_user_project_domain_resource(result, context,
                                                      mock_resource)
