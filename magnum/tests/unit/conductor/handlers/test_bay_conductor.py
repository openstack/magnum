# Copyright 2014 NEC Corporation.  All rights reserved.
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
import uuid

from heatclient import exc
from oslo_service import loopingcall

from magnum.common import exception
from magnum.conductor.handlers import bay_conductor
from magnum import objects
from magnum.objects.fields import BayStatus as bay_status
from magnum.tests import base
from magnum.tests.unit.db import base as db_base
from magnum.tests.unit.db import utils

import mock
from mock import patch
from oslo_config import cfg


class TestBayConductorWithK8s(base.TestCase):
    def setUp(self):
        super(TestBayConductorWithK8s, self).setUp()
        self.baymodel_dict = {
            'image_id': 'image_id',
            'flavor_id': 'flavor_id',
            'master_flavor_id': 'master_flavor_id',
            'keypair_id': 'keypair_id',
            'dns_nameserver': 'dns_nameserver',
            'external_network_id': 'external_network_id',
            'fixed_network': '10.20.30.0/24',
            'network_driver': 'network_driver',
            'docker_volume_size': 20,
            'cluster_distro': 'fedora-atomic',
            'ssh_authorized_key': 'ssh_authorized_key',
            'coe': 'kubernetes',
            'token': None,
            'http_proxy': 'http_proxy',
            'https_proxy': 'https_proxy',
            'no_proxy': 'no_proxy',
            'labels': {'flannel_network_cidr': '10.101.0.0/16',
                       'flannel_network_subnetlen': '26',
                       'flannel_use_vxlan': 'yes'},
        }
        self.bay_dict = {
            'baymodel_id': 'xx-xx-xx-xx',
            'name': 'bay1',
            'stack_id': 'xx-xx-xx-xx',
            'api_address': '172.17.2.3',
            'node_addresses': ['172.17.2.4'],
            'node_count': 1,
            'master_count': 1,
            'discovery_url': 'https://discovery.etcd.io/test',
            'master_addresses': ['172.17.2.18'],
            'ca_cert_ref': 'http://barbican/v1/containers/xx-xx-xx-xx',
            'magnum_cert_ref': 'http://barbican/v1/containers/xx-xx-xx-xx',
        }

    @patch('magnum.objects.BayModel.get_by_uuid')
    def test_extract_template_definition(
            self,
            mock_objects_baymodel_get_by_uuid):
        self._test_extract_template_definition(
            mock_objects_baymodel_get_by_uuid)

    def _test_extract_template_definition(
            self,
            mock_objects_baymodel_get_by_uuid,
            missing_attr=None):
        if missing_attr in self.baymodel_dict:
            self.baymodel_dict[missing_attr] = None
        elif missing_attr in self.bay_dict:
            self.bay_dict[missing_attr] = None
        baymodel = objects.BayModel(self.context, **self.baymodel_dict)
        mock_objects_baymodel_get_by_uuid.return_value = baymodel
        bay = objects.Bay(self.context, **self.bay_dict)

        (template_path,
         definition) = bay_conductor._extract_template_definition(self.context,
                                                                  bay)

        mapping = {
            'dns_nameserver': 'dns_nameserver',
            'image_id': 'server_image',
            'flavor_id': 'minion_flavor',
            'docker_volume_size': 'docker_volume_size',
            'fixed_network': 'fixed_network_cidr',
            'network_driver': 'network_driver',
            'master_flavor_id': 'master_flavor',
            'apiserver_port': '',
            'node_count': 'number_of_minions',
            'master_count': 'number_of_masters',
            'discovery_url': 'discovery_url',
            'labels': {'flannel_network_cidr': '10.101.0.0/16',
                       'flannel_network_subnetlen': '26',
                       'flannel_use_vxlan': 'yes'},
            'http_proxy': 'http_proxy',
            'https_proxy': 'https_proxy',
            'no_proxy': 'no_proxy',
        }
        expected = {
            'ssh_key_name': 'keypair_id',
            'external_network': 'external_network_id',
            'network_driver': 'network_driver',
            'dns_nameserver': 'dns_nameserver',
            'server_image': 'image_id',
            'minion_flavor': 'flavor_id',
            'master_flavor': 'master_flavor_id',
            'number_of_minions': '1',
            'number_of_masters': '1',
            'fixed_network_cidr': '10.20.30.0/24',
            'docker_volume_size': 20,
            'discovery_url': 'https://discovery.etcd.io/test',
            'flannel_network_cidr': '10.101.0.0/16',
            'flannel_network_subnetlen': '26',
            'flannel_use_vxlan': 'yes',
            'http_proxy': 'http_proxy',
            'https_proxy': 'https_proxy',
            'no_proxy': 'no_proxy',
        }
        if missing_attr is not None:
            expected.pop(mapping[missing_attr], None)

        self.assertEqual(expected, definition)

    @patch('requests.get')
    @patch('magnum.objects.BayModel.get_by_uuid')
    def test_extract_template_definition_coreos_with_disovery(
            self,
            mock_objects_baymodel_get_by_uuid,
            reqget):
        baymodel_dict = self.baymodel_dict
        baymodel_dict['cluster_distro'] = 'coreos'
        cfg.CONF.set_override('coreos_discovery_token_url',
                              'http://tokentest',
                              group='bay')
        mock_req = mock.MagicMock(text='/h1/h2/h3')
        reqget.return_value = mock_req
        baymodel = objects.BayModel(self.context, **self.baymodel_dict)
        mock_objects_baymodel_get_by_uuid.return_value = baymodel
        bay = objects.Bay(self.context, **self.bay_dict)

        (template_path,
         definition) = bay_conductor._extract_template_definition(self.context,
                                                                  bay)

        expected = {
            'ssh_key_name': 'keypair_id',
            'external_network': 'external_network_id',
            'dns_nameserver': 'dns_nameserver',
            'server_image': 'image_id',
            'minion_flavor': 'flavor_id',
            'master_flavor': 'master_flavor_id',
            'number_of_minions': '1',
            'number_of_masters': '1',
            'fixed_network_cidr': '10.20.30.0/24',
            'network_driver': 'network_driver',
            'docker_volume_size': 20,
            'ssh_authorized_key': 'ssh_authorized_key',
            'token': 'h3',
            'discovery_url': 'https://discovery.etcd.io/test',
            'http_proxy': 'http_proxy',
            'https_proxy': 'https_proxy',
            'no_proxy': 'no_proxy',
            'flannel_network_cidr': '10.101.0.0/16',
            'flannel_network_subnetlen': '26',
            'flannel_use_vxlan': 'yes',
        }
        self.assertEqual(expected, definition)

    @patch('uuid.uuid4')
    @patch('magnum.objects.BayModel.get_by_uuid')
    def test_extract_template_definition_coreos_no_discoveryurl(
            self,
            mock_objects_baymodel_get_by_uuid,
            mock_uuid):
        baymodel_dict = self.baymodel_dict
        baymodel_dict['cluster_distro'] = 'coreos'
        cfg.CONF.set_override('coreos_discovery_token_url',
                              None,
                              group='bay')
        mock_uuid.return_value = mock.MagicMock(
            hex='ba3d1866282848ddbedc76112110c208')
        baymodel = objects.BayModel(self.context, **self.baymodel_dict)
        mock_objects_baymodel_get_by_uuid.return_value = baymodel
        bay = objects.Bay(self.context, **self.bay_dict)

        (template_path,
         definition) = bay_conductor._extract_template_definition(self.context,
                                                                  bay)

        expected = {
            'ssh_key_name': 'keypair_id',
            'external_network': 'external_network_id',
            'dns_nameserver': 'dns_nameserver',
            'server_image': 'image_id',
            'minion_flavor': 'flavor_id',
            'master_flavor': 'master_flavor_id',
            'number_of_minions': '1',
            'number_of_masters': '1',
            'fixed_network_cidr': '10.20.30.0/24',
            'network_driver': 'network_driver',
            'docker_volume_size': 20,
            'ssh_authorized_key': 'ssh_authorized_key',
            'token': 'ba3d1866282848ddbedc76112110c208',
            'discovery_url': 'https://discovery.etcd.io/test',
            'http_proxy': 'http_proxy',
            'https_proxy': 'https_proxy',
            'no_proxy': 'no_proxy',
            'flannel_network_cidr': '10.101.0.0/16',
            'flannel_network_subnetlen': '26',
            'flannel_use_vxlan': 'yes',
        }
        self.assertEqual(expected, definition)

    @patch('magnum.objects.BayModel.get_by_uuid')
    def test_extract_template_definition_without_dns(
            self,
            mock_objects_baymodel_get_by_uuid):
        self._test_extract_template_definition(
            mock_objects_baymodel_get_by_uuid,
            missing_attr='dns_nameserver')

    @patch('magnum.objects.BayModel.get_by_uuid')
    def test_extract_template_definition_without_server_image(
            self,
            mock_objects_baymodel_get_by_uuid):
        self._test_extract_template_definition(
            mock_objects_baymodel_get_by_uuid,
            missing_attr='image_id')

    @patch('magnum.objects.BayModel.get_by_uuid')
    def test_extract_template_definition_without_minion_flavor(
            self,
            mock_objects_baymodel_get_by_uuid):
        self._test_extract_template_definition(
            mock_objects_baymodel_get_by_uuid,
            missing_attr='flavor_id')

    @patch('magnum.objects.BayModel.get_by_uuid')
    def test_extract_template_definition_without_docker_volume_size(
            self,
            mock_objects_baymodel_get_by_uuid):
        self._test_extract_template_definition(
            mock_objects_baymodel_get_by_uuid,
            missing_attr='docker_volume_size')

    @patch('magnum.objects.BayModel.get_by_uuid')
    def test_extract_template_definition_without_fixed_network(
            self,
            mock_objects_baymodel_get_by_uuid):
        self._test_extract_template_definition(
            mock_objects_baymodel_get_by_uuid,
            missing_attr='fixed_network')

    @patch('magnum.objects.BayModel.get_by_uuid')
    def test_extract_template_definition_without_master_flavor(
            self,
            mock_objects_baymodel_get_by_uuid):
        self._test_extract_template_definition(
            mock_objects_baymodel_get_by_uuid,
            missing_attr='master_flavor_id')

    @patch('magnum.objects.BayModel.get_by_uuid')
    def test_extract_template_definition_without_ssh_authorized_key(
            self,
            mock_objects_baymodel_get_by_uuid):
        baymodel_dict = self.baymodel_dict
        baymodel_dict['cluster_distro'] = 'coreos'
        baymodel_dict['ssh_authorized_key'] = None
        baymodel = objects.BayModel(self.context, **baymodel_dict)
        mock_objects_baymodel_get_by_uuid.return_value = baymodel
        bay = objects.Bay(self.context, **self.bay_dict)

        (template_path,
         definition) = bay_conductor._extract_template_definition(self.context,
                                                                  bay)

        expected = {
            'ssh_key_name': 'keypair_id',
            'external_network': 'external_network_id',
            'dns_nameserver': 'dns_nameserver',
            'server_image': 'image_id',
            'master_flavor': 'master_flavor_id',
            'minion_flavor': 'flavor_id',
            'number_of_minions': '1',
            'number_of_masters': '1',
            'fixed_network_cidr': '10.20.30.0/24',
            'network_driver': 'network_driver',
            'docker_volume_size': 20,
            'discovery_url': 'https://discovery.etcd.io/test',
            'http_proxy': 'http_proxy',
            'https_proxy': 'https_proxy',
            'no_proxy': 'no_proxy',
            'flannel_network_cidr': '10.101.0.0/16',
            'flannel_network_subnetlen': '26',
            'flannel_use_vxlan': 'yes',
        }
        self.assertIn('token', definition)
        del definition['token']
        self.assertEqual(expected, definition)

    @patch('magnum.objects.BayModel.get_by_uuid')
    def test_extract_template_definition_without_apiserver_port(
            self,
            mock_objects_baymodel_get_by_uuid):
        self._test_extract_template_definition(
            mock_objects_baymodel_get_by_uuid,
            missing_attr='apiserver_port')

    @patch('magnum.objects.BayModel.get_by_uuid')
    def test_extract_template_definition_without_node_count(
            self,
            mock_objects_baymodel_get_by_uuid):
        self._test_extract_template_definition(
            mock_objects_baymodel_get_by_uuid,
            missing_attr='node_count')

    @patch('magnum.objects.BayModel.get_by_uuid')
    def test_extract_template_definition_without_master_count(
            self,
            mock_objects_baymodel_get_by_uuid):
        self._test_extract_template_definition(
            mock_objects_baymodel_get_by_uuid,
            missing_attr='master_count')

    @patch('requests.get')
    @patch('magnum.objects.BayModel.get_by_uuid')
    def test_extract_template_definition_without_discovery_url(
            self,
            mock_objects_baymodel_get_by_uuid,
            reqget):
        baymodel = objects.BayModel(self.context, **self.baymodel_dict)
        mock_objects_baymodel_get_by_uuid.return_value = baymodel
        bay_dict = self.bay_dict
        bay_dict['discovery_url'] = None
        bay = objects.Bay(self.context, **bay_dict)

        cfg.CONF.set_override('etcd_discovery_service_endpoint_format',
                              'http://etcd/test?size=%(size)d',
                              group='bay')
        mock_req = mock.MagicMock(text='https://address/token')
        reqget.return_value = mock_req

        (template_path,
         definition) = bay_conductor._extract_template_definition(self.context,
                                                                  bay)

        expected = {
            'ssh_key_name': 'keypair_id',
            'external_network': 'external_network_id',
            'dns_nameserver': 'dns_nameserver',
            'server_image': 'image_id',
            'master_flavor': 'master_flavor_id',
            'minion_flavor': 'flavor_id',
            'number_of_minions': '1',
            'number_of_masters': '1',
            'fixed_network_cidr': '10.20.30.0/24',
            'network_driver': 'network_driver',
            'docker_volume_size': 20,
            'discovery_url': 'https://address/token',
            'http_proxy': 'http_proxy',
            'https_proxy': 'https_proxy',
            'no_proxy': 'no_proxy',
            'flannel_network_cidr': '10.101.0.0/16',
            'flannel_network_subnetlen': '26',
            'flannel_use_vxlan': 'yes',
        }
        self.assertEqual(expected, definition)
        reqget.assert_called_once_with('http://etcd/test?size=1')

    @patch('magnum.common.short_id.generate_id')
    @patch('heatclient.common.template_utils.get_template_contents')
    @patch('magnum.conductor.handlers.bay_conductor'
           '._extract_template_definition')
    def test_create_stack(self,
                          mock_extract_template_definition,
                          mock_get_template_contents,
                          mock_generate_id):

        mock_generate_id.return_value = 'xx-xx-xx-xx'
        expected_stack_name = 'expected_stack_name-xx-xx-xx-xx'
        expected_template_contents = 'template_contents'
        exptected_files = []
        dummy_bay_name = 'expected_stack_name'
        expected_timeout = 15

        mock_tpl_files = mock.MagicMock()
        mock_tpl_files.items.return_value = exptected_files
        mock_get_template_contents.return_value = [
            mock_tpl_files, expected_template_contents]
        mock_extract_template_definition.return_value = ('template/path',
                                                         {})
        mock_heat_client = mock.MagicMock()
        mock_osc = mock.MagicMock()
        mock_osc.heat.return_value = mock_heat_client
        mock_bay = mock.MagicMock()
        mock_bay.name = dummy_bay_name

        bay_conductor._create_stack(self.context, mock_osc,
                                    mock_bay, expected_timeout)

        expected_args = {
            'stack_name': expected_stack_name,
            'parameters': {},
            'template': expected_template_contents,
            'files': dict(exptected_files),
            'timeout_mins': expected_timeout
        }
        mock_heat_client.stacks.create.assert_called_once_with(**expected_args)

    @patch('magnum.common.short_id.generate_id')
    @patch('heatclient.common.template_utils.get_template_contents')
    @patch('magnum.conductor.handlers.bay_conductor'
           '._extract_template_definition')
    def test_create_stack_no_timeout_specified(
            self,
            mock_extract_template_definition,
            mock_get_template_contents,
            mock_generate_id):

        mock_generate_id.return_value = 'xx-xx-xx-xx'
        expected_stack_name = 'expected_stack_name-xx-xx-xx-xx'
        expected_template_contents = 'template_contents'
        exptected_files = []
        dummy_bay_name = 'expected_stack_name'
        expected_timeout = cfg.CONF.bay_heat.bay_create_timeout

        mock_tpl_files = mock.MagicMock()
        mock_tpl_files.items.return_value = exptected_files
        mock_get_template_contents.return_value = [
            mock_tpl_files, expected_template_contents]
        mock_extract_template_definition.return_value = ('template/path',
                                                         {})
        mock_heat_client = mock.MagicMock()
        mock_osc = mock.MagicMock()
        mock_osc.heat.return_value = mock_heat_client
        mock_bay = mock.MagicMock()
        mock_bay.name = dummy_bay_name

        bay_conductor._create_stack(self.context, mock_osc,
                                    mock_bay, None)

        expected_args = {
            'stack_name': expected_stack_name,
            'parameters': {},
            'template': expected_template_contents,
            'files': dict(exptected_files),
            'timeout_mins': expected_timeout
        }
        mock_heat_client.stacks.create.assert_called_once_with(**expected_args)

    @patch('magnum.common.short_id.generate_id')
    @patch('heatclient.common.template_utils.get_template_contents')
    @patch('magnum.conductor.handlers.bay_conductor'
           '._extract_template_definition')
    def test_create_stack_timeout_is_zero(
            self,
            mock_extract_template_definition,
            mock_get_template_contents,
            mock_generate_id):

        mock_generate_id.return_value = 'xx-xx-xx-xx'
        expected_stack_name = 'expected_stack_name-xx-xx-xx-xx'
        expected_template_contents = 'template_contents'
        exptected_files = []
        dummy_bay_name = 'expected_stack_name'
        bay_timeout = 0
        expected_timeout = None

        mock_tpl_files = mock.MagicMock()
        mock_tpl_files.items.return_value = exptected_files
        mock_get_template_contents.return_value = [
            mock_tpl_files, expected_template_contents]
        mock_extract_template_definition.return_value = ('template/path',
                                                         {})
        mock_heat_client = mock.MagicMock()
        mock_osc = mock.MagicMock()
        mock_osc.heat.return_value = mock_heat_client
        mock_bay = mock.MagicMock()
        mock_bay.name = dummy_bay_name

        bay_conductor._create_stack(self.context, mock_osc,
                                    mock_bay, bay_timeout)

        expected_args = {
            'stack_name': expected_stack_name,
            'parameters': {},
            'template': expected_template_contents,
            'files': dict(exptected_files),
            'timeout_mins': expected_timeout
        }
        mock_heat_client.stacks.create.assert_called_once_with(**expected_args)

    @patch('heatclient.common.template_utils.get_template_contents')
    @patch('magnum.conductor.handlers.bay_conductor'
           '._extract_template_definition')
    def test_update_stack(self,
                          mock_extract_template_definition,
                          mock_get_template_contents):

        mock_stack_id = 'xx-xx-xx-xx'
        expected_template_contents = 'template_contents'
        exptected_files = []

        mock_tpl_files = mock.MagicMock()
        mock_tpl_files.items.return_value = exptected_files
        mock_get_template_contents.return_value = [
            mock_tpl_files, expected_template_contents]
        mock_extract_template_definition.return_value = ('template/path',
                                                         {})
        mock_heat_client = mock.MagicMock()
        mock_osc = mock.MagicMock()
        mock_osc.heat.return_value = mock_heat_client
        mock_bay = mock.MagicMock()
        mock_bay.stack_id = mock_stack_id

        bay_conductor._update_stack({}, mock_osc, mock_bay)

        expected_args = {
            'parameters': {},
            'template': expected_template_contents,
            'files': dict(exptected_files)
        }
        mock_heat_client.stacks.update.assert_called_once_with(mock_stack_id,
                                                               **expected_args)

    @patch('magnum.conductor.utils.retrieve_baymodel')
    @patch('oslo_config.cfg')
    @patch('magnum.common.clients.OpenStackClients')
    def setup_poll_test(self, mock_openstack_client, cfg,
                        mock_retrieve_baymodel):
        cfg.CONF.bay_heat.max_attempts = 10
        bay = mock.MagicMock()
        mock_heat_stack = mock.MagicMock()
        mock_heat_client = mock.MagicMock()
        mock_heat_client.stacks.get.return_value = mock_heat_stack
        mock_openstack_client.heat.return_value = mock_heat_client
        baymodel = objects.BayModel(self.context, **self.baymodel_dict)
        mock_retrieve_baymodel.return_value = baymodel
        poller = bay_conductor.HeatPoller(mock_openstack_client, bay)
        return (mock_heat_stack, bay, poller)

    def test_poll_no_save(self):
        mock_heat_stack, bay, poller = self.setup_poll_test()

        bay.status = bay_status.CREATE_IN_PROGRESS
        mock_heat_stack.stack_status = bay_status.CREATE_IN_PROGRESS
        poller.poll_and_check()

        self.assertEqual(bay.save.call_count, 0)
        self.assertEqual(poller.attempts, 1)

    def test_poll_save(self):
        mock_heat_stack, bay, poller = self.setup_poll_test()

        bay.status = bay_status.CREATE_IN_PROGRESS
        mock_heat_stack.stack_status = bay_status.CREATE_FAILED
        mock_heat_stack.stack_status_reason = 'Create failed'
        self.assertRaises(loopingcall.LoopingCallDone, poller.poll_and_check)

        self.assertEqual(bay.save.call_count, 1)
        self.assertEqual(bay.status, bay_status.CREATE_FAILED)
        self.assertEqual(bay.status_reason, 'Create failed')
        self.assertEqual(poller.attempts, 1)

    def test_poll_done(self):
        mock_heat_stack, bay, poller = self.setup_poll_test()

        mock_heat_stack.stack_status = bay_status.DELETE_COMPLETE
        self.assertRaises(loopingcall.LoopingCallDone, poller.poll_and_check)

        mock_heat_stack.stack_status = bay_status.CREATE_FAILED
        self.assertRaises(loopingcall.LoopingCallDone, poller.poll_and_check)
        self.assertEqual(poller.attempts, 2)

    def test_poll_done_by_update(self):
        mock_heat_stack, bay, poller = self.setup_poll_test()

        mock_heat_stack.stack_status = bay_status.UPDATE_COMPLETE
        mock_heat_stack.parameters = {'number_of_minions': 2}
        self.assertRaises(loopingcall.LoopingCallDone, poller.poll_and_check)

        self.assertEqual(bay.save.call_count, 1)
        self.assertEqual(bay.status, bay_status.UPDATE_COMPLETE)
        self.assertEqual(bay.node_count, 2)
        self.assertEqual(poller.attempts, 1)

    def test_poll_done_by_update_failed(self):
        mock_heat_stack, bay, poller = self.setup_poll_test()

        mock_heat_stack.stack_status = bay_status.UPDATE_FAILED
        mock_heat_stack.parameters = {'number_of_minions': 2}
        self.assertRaises(loopingcall.LoopingCallDone, poller.poll_and_check)

        self.assertEqual(bay.save.call_count, 1)
        self.assertEqual(bay.status, bay_status.UPDATE_FAILED)
        self.assertEqual(bay.node_count, 2)
        self.assertEqual(poller.attempts, 1)

    def test_poll_destroy(self):
        mock_heat_stack, bay, poller = self.setup_poll_test()

        mock_heat_stack.stack_status = bay_status.DELETE_FAILED
        self.assertRaises(loopingcall.LoopingCallDone, poller.poll_and_check)
        # Destroy method is not called when stack delete failed
        self.assertEqual(bay.destroy.call_count, 0)

        mock_heat_stack.stack_status = bay_status.DELETE_IN_PROGRESS
        poller.poll_and_check()
        self.assertEqual(bay.destroy.call_count, 0)
        self.assertEqual(bay.status, bay_status.DELETE_IN_PROGRESS)

        mock_heat_stack.stack_status = bay_status.DELETE_COMPLETE
        self.assertRaises(loopingcall.LoopingCallDone, poller.poll_and_check)
        # The bay status should still be DELETE_IN_PROGRESS, because
        # the destroy() method may be failed. If success, this bay record
        # will delete directly, change status is meaningless.
        self.assertEqual(bay.status, bay_status.DELETE_IN_PROGRESS)
        self.assertEqual(bay.destroy.call_count, 1)

    def test_poll_delete_in_progress_timeout_set(self):
        mock_heat_stack, bay, poller = self.setup_poll_test()

        mock_heat_stack.stack_status = bay_status.DELETE_IN_PROGRESS
        mock_heat_stack.timeout_mins = 60
        # timeout only affects stack creation so expecting this
        # to process normally
        poller.poll_and_check()

    def test_poll_delete_in_progress_max_attempts_reached(self):
        mock_heat_stack, bay, poller = self.setup_poll_test()

        mock_heat_stack.stack_status = bay_status.DELETE_IN_PROGRESS
        poller.attempts = cfg.CONF.bay_heat.max_attempts
        self.assertRaises(loopingcall.LoopingCallDone, poller.poll_and_check)

    def test_poll_create_in_prog_max_att_reached_no_timeout(self):
        mock_heat_stack, bay, poller = self.setup_poll_test()

        mock_heat_stack.stack_status = bay_status.CREATE_IN_PROGRESS
        poller.attempts = cfg.CONF.bay_heat.max_attempts
        mock_heat_stack.timeout_mins = None
        self.assertRaises(loopingcall.LoopingCallDone, poller.poll_and_check)

    def test_poll_create_in_prog_max_att_reached_timeout_set(self):
        mock_heat_stack, bay, poller = self.setup_poll_test()

        mock_heat_stack.stack_status = bay_status.CREATE_IN_PROGRESS
        poller.attempts = cfg.CONF.bay_heat.max_attempts
        mock_heat_stack.timeout_mins = 60
        # since the timeout is set the max attempts gets ignored since
        # the timeout will eventually stop the poller either when
        # the stack gets created or the timeout gets reached
        poller.poll_and_check()

    def test_poll_create_in_prog_max_att_reached_timed_out(self):
        mock_heat_stack, bay, poller = self.setup_poll_test()

        mock_heat_stack.stack_status = bay_status.CREATE_FAILED
        poller.attempts = cfg.CONF.bay_heat.max_attempts
        mock_heat_stack.timeout_mins = 60
        self.assertRaises(loopingcall.LoopingCallDone, poller.poll_and_check)

    def test_poll_create_in_prog_max_att_not_reached_no_timeout(self):
        mock_heat_stack, bay, poller = self.setup_poll_test()

        mock_heat_stack.stack_status = bay_status.CREATE_IN_PROGRESS
        mock_heat_stack.timeout.mins = None
        poller.poll_and_check()

    def test_poll_create_in_prog_max_att_not_reached_timeout_set(self):
        mock_heat_stack, bay, poller = self.setup_poll_test()

        mock_heat_stack.stack_status = bay_status.CREATE_IN_PROGRESS
        mock_heat_stack.timeout_mins = 60
        poller.poll_and_check()

    def test_poll_create_in_prog_max_att_not_reached_timed_out(self):
        mock_heat_stack, bay, poller = self.setup_poll_test()

        mock_heat_stack.stack_status = bay_status.CREATE_FAILED
        mock_heat_stack.timeout_mins = 60
        self.assertRaises(loopingcall.LoopingCallDone, poller.poll_and_check)

    def test_poll_node_count(self):
        mock_heat_stack, bay, poller = self.setup_poll_test()

        mock_heat_stack.parameters = {'number_of_minions': 1}
        mock_heat_stack.stack_status = bay_status.CREATE_IN_PROGRESS
        poller.poll_and_check()

        self.assertEqual(bay.node_count, 1)

    def test_poll_node_count_by_update(self):
        mock_heat_stack, bay, poller = self.setup_poll_test()

        mock_heat_stack.parameters = {'number_of_minions': 2}
        mock_heat_stack.stack_status = bay_status.UPDATE_COMPLETE
        self.assertRaises(loopingcall.LoopingCallDone, poller.poll_and_check)

        self.assertEqual(bay.node_count, 2)


class TestHandler(db_base.DbTestCase):

    def setUp(self):
        super(TestHandler, self).setUp()
        self.handler = bay_conductor.Handler()
        baymodel_dict = utils.get_test_baymodel()
        self.baymodel = objects.BayModel(self.context, **baymodel_dict)
        self.baymodel.create()
        bay_dict = utils.get_test_bay(node_count=1)
        self.bay = objects.Bay(self.context, **bay_dict)
        self.bay.create()

    @patch('magnum.conductor.scale_manager.ScaleManager')
    @patch('magnum.conductor.handlers.bay_conductor.Handler._poll_and_check')
    @patch('magnum.conductor.handlers.bay_conductor._update_stack')
    @patch('magnum.common.clients.OpenStackClients')
    def test_update_node_count_success(
            self, mock_openstack_client_class,
            mock_update_stack, mock_poll_and_check,
            mock_scale_manager):
        def side_effect(*args, **kwargs):
            self.bay.node_count = 2
            self.bay.save()
        mock_poll_and_check.side_effect = side_effect
        mock_heat_stack = mock.MagicMock()
        mock_heat_stack.stack_status = bay_status.CREATE_COMPLETE
        mock_heat_client = mock.MagicMock()
        mock_heat_client.stacks.get.return_value = mock_heat_stack
        mock_openstack_client = mock_openstack_client_class.return_value
        mock_openstack_client.heat.return_value = mock_heat_client

        self.bay.node_count = 2
        self.handler.bay_update(self.context, self.bay)

        mock_update_stack.assert_called_once_with(
            self.context, mock_openstack_client, self.bay,
            mock_scale_manager.return_value)
        bay = objects.Bay.get(self.context, self.bay.uuid)
        self.assertEqual(bay.node_count, 2)

    @patch('magnum.conductor.handlers.bay_conductor.Handler._poll_and_check')
    @patch('magnum.conductor.handlers.bay_conductor._update_stack')
    @patch('magnum.common.clients.OpenStackClients')
    def test_update_node_count_failure(
            self, mock_openstack_client_class,
            mock_update_stack, mock_poll_and_check):
        def side_effect(*args, **kwargs):
            self.bay.node_count = 2
            self.bay.save()
        mock_poll_and_check.side_effect = side_effect
        mock_heat_stack = mock.MagicMock()
        mock_heat_stack.stack_status = bay_status.CREATE_FAILED
        mock_heat_client = mock.MagicMock()
        mock_heat_client.stacks.get.return_value = mock_heat_stack
        mock_openstack_client = mock_openstack_client_class.return_value
        mock_openstack_client.heat.return_value = mock_heat_client

        self.bay.node_count = 2
        self.assertRaises(exception.NotSupported, self.handler.bay_update,
                          self.context, self.bay)

        bay = objects.Bay.get(self.context, self.bay.uuid)
        self.assertEqual(bay.node_count, 1)

    @patch('magnum.common.clients.OpenStackClients')
    def test_update_bay_with_invalid_params(
            self, mock_openstack_client_class):
        mock_heat_stack = mock.MagicMock()
        mock_heat_stack.stack_status = bay_status.CREATE_COMPLETE
        mock_heat_client = mock.MagicMock()
        mock_heat_client.stacks.get.return_value = mock_heat_stack
        mock_openstack_client = mock_openstack_client_class.return_value
        mock_openstack_client.heat.return_value = mock_heat_client

        self.bay.node_count = 2
        self.bay.api_address = '7.7.7.7'
        self.assertRaises(exception.InvalidParameterValue,
                          self.handler.bay_update,
                          self.context,
                          self.bay)
        bay = objects.Bay.get(self.context, self.bay.uuid)
        self.assertEqual(bay.node_count, 1)

    @patch('magnum.conductor.handlers.bay_conductor.HeatPoller')
    @patch('magnum.conductor.handlers.bay_conductor.cert_manager')
    @patch('magnum.conductor.handlers.bay_conductor._create_stack')
    @patch('magnum.conductor.handlers.bay_conductor.uuid')
    @patch('magnum.common.clients.OpenStackClients')
    def test_create(self, mock_openstack_client_class, mock_uuid,
                    mock_create_stack, mock_cert_manager,
                    mock_heat_poller_class):
        timeout = 15
        test_uuid = uuid.uuid4()
        mock_uuid.uuid4.return_value = test_uuid
        mock_poller = mock.MagicMock()
        mock_poller.poll_and_check.return_value = loopingcall.LoopingCallDone()
        mock_heat_poller_class.return_value = mock_poller
        mock_openstack_client_class.return_value = mock.sentinel.osc

        def create_stack_side_effect(context, osc, bay, timeout):
            self.assertEqual(bay.uuid, str(test_uuid))
            return {'stack': {'id': 'stack-id'}}

        mock_create_stack.side_effect = create_stack_side_effect

        self.handler.bay_create(self.context,
                                self.bay, timeout)

        mock_create_stack.assert_called_once_with(self.context,
                                                  mock.sentinel.osc,
                                                  self.bay, timeout)
        mock_cert_manager.generate_certificates_to_bay.assert_called_once_with(
            self.bay)

    @patch('magnum.conductor.handlers.bay_conductor.cert_manager')
    @patch('magnum.conductor.handlers.bay_conductor._create_stack')
    @patch('magnum.common.clients.OpenStackClients')
    def test_create_handles_bad_request(self, mock_openstack_client_class,
                                        mock_create_stack,
                                        mock_cert_manager):
        mock_create_stack.side_effect = exc.HTTPBadRequest
        timeout = 15
        self.assertRaises(exception.InvalidParameterValue,
                          self.handler.bay_create, self.context,
                          self.bay, timeout)
        mock_cert_manager.generate_certificates_to_bay.assert_called_once_with(
            self.bay)
        mock_cert_manager.delete_certificates_from_bay(self.bay)

    @patch('magnum.common.clients.OpenStackClients')
    def test_bay_delete(self, mock_openstack_client_class):
        osc = mock.MagicMock()
        mock_openstack_client_class.return_value = osc
        osc.heat.side_effect = exc.HTTPNotFound
        self.handler.bay_delete(self.context, self.bay.uuid)
        # The bay has been destroyed
        self.assertRaises(exception.BayNotFound,
                          objects.Bay.get, self.context, self.bay.uuid)


class TestBayConductorWithSwarm(base.TestCase):
    def setUp(self):
        super(TestBayConductorWithSwarm, self).setUp()
        self.baymodel_dict = {
            'image_id': 'image_id',
            'flavor_id': 'flavor_id',
            'keypair_id': 'keypair_id',
            'dns_nameserver': 'dns_nameserver',
            'external_network_id': 'external_network_id',
            'fixed_network': '10.2.0.0/22',
            'cluster_distro': 'fedora-atomic',
            'coe': 'swarm',
            'http_proxy': 'http_proxy',
            'https_proxy': 'https_proxy',
            'no_proxy': 'no_proxy',
            'insecure': False
        }
        self.bay_dict = {
            'id': 1,
            'uuid': 'some_uuid',
            'baymodel_id': 'xx-xx-xx-xx',
            'name': 'bay1',
            'stack_id': 'xx-xx-xx-xx',
            'api_address': '172.17.2.3',
            'node_addresses': ['172.17.2.4'],
            'node_count': 1,
            'discovery_url': 'token://39987da72f8386e0d0225ae8929e7cb4',
        }
        osc_patcher = mock.patch('magnum.common.clients.OpenStackClients')
        self.mock_osc_class = osc_patcher.start()
        self.addCleanup(osc_patcher.stop)
        self.mock_osc = mock.MagicMock()
        self.mock_osc.magnum_url.return_value = 'http://127.0.0.1:9511/v1'
        self.mock_osc_class.return_value = self.mock_osc

    @patch('magnum.objects.BayModel.get_by_uuid')
    def test_extract_template_definition_all_values(
            self,
            mock_objects_baymodel_get_by_uuid):
        baymodel = objects.BayModel(self.context, **self.baymodel_dict)
        mock_objects_baymodel_get_by_uuid.return_value = baymodel
        bay = objects.Bay(self.context, **self.bay_dict)

        (template_path,
         definition) = bay_conductor._extract_template_definition(self.context,
                                                                  bay)

        expected = {
            'ssh_key_name': 'keypair_id',
            'external_network': 'external_network_id',
            'dns_nameserver': 'dns_nameserver',
            'server_image': 'image_id',
            'server_flavor': 'flavor_id',
            'number_of_nodes': '1',
            'fixed_network_cidr': '10.2.0.0/22',
            'discovery_url': 'token://39987da72f8386e0d0225ae8929e7cb4',
            'http_proxy': 'http_proxy',
            'https_proxy': 'https_proxy',
            'no_proxy': 'no_proxy',
            'user_token': self.context.auth_token,
            'bay_uuid': 'some_uuid',
            'magnum_url': self.mock_osc.magnum_url.return_value,
            'insecure': False

        }
        self.assertEqual(expected, definition)

    @patch('magnum.objects.BayModel.get_by_uuid')
    def test_extract_template_definition_only_required(
            self,
            mock_objects_baymodel_get_by_uuid):
        cfg.CONF.set_override('public_swarm_discovery', False, group='bay')
        cfg.CONF.set_override('swarm_discovery_url_format',
                              'test_discovery', group='bay')

        not_required = ['image_id', 'flavor_id', 'dns_nameserver',
                        'fixed_network', 'http_proxy', 'https_proxy',
                        'no_proxy']
        for key in not_required:
            self.baymodel_dict[key] = None
        self.bay_dict['discovery_url'] = None

        baymodel = objects.BayModel(self.context, **self.baymodel_dict)
        mock_objects_baymodel_get_by_uuid.return_value = baymodel
        bay = objects.Bay(self.context, **self.bay_dict)

        (template_path,
         definition) = bay_conductor._extract_template_definition(self.context,
                                                                  bay)

        expected = {
            'ssh_key_name': 'keypair_id',
            'external_network': 'external_network_id',
            'number_of_nodes': '1',
            'discovery_url': 'test_discovery',
            'user_token': self.context.auth_token,
            'bay_uuid': 'some_uuid',
            'magnum_url': self.mock_osc.magnum_url.return_value,
            'insecure': False
        }
        self.assertEqual(expected, definition)

    @patch('magnum.conductor.utils.retrieve_baymodel')
    @patch('oslo_config.cfg')
    @patch('magnum.common.clients.OpenStackClients')
    def setup_poll_test(self, mock_openstack_client, cfg,
                        mock_retrieve_baymodel):
        cfg.CONF.bay_heat.max_attempts = 10
        bay = mock.MagicMock()
        mock_heat_stack = mock.MagicMock()
        mock_heat_client = mock.MagicMock()
        mock_heat_client.stacks.get.return_value = mock_heat_stack
        mock_openstack_client.heat.return_value = mock_heat_client
        baymodel = objects.BayModel(self.context, **self.baymodel_dict)
        mock_retrieve_baymodel.return_value = baymodel
        poller = bay_conductor.HeatPoller(mock_openstack_client, bay)
        return (mock_heat_stack, bay, poller)

    def test_poll_node_count(self):
        mock_heat_stack, bay, poller = self.setup_poll_test()

        mock_heat_stack.parameters = {'number_of_nodes': 1}
        mock_heat_stack.stack_status = bay_status.CREATE_IN_PROGRESS
        poller.poll_and_check()

        self.assertEqual(bay.node_count, 1)

    def test_poll_node_count_by_update(self):
        mock_heat_stack, bay, poller = self.setup_poll_test()

        mock_heat_stack.parameters = {'number_of_nodes': 2}
        mock_heat_stack.stack_status = bay_status.UPDATE_COMPLETE
        self.assertRaises(loopingcall.LoopingCallDone, poller.poll_and_check)

        self.assertEqual(bay.node_count, 2)


class TestBayConductorWithMesos(base.TestCase):
    def setUp(self):
        super(TestBayConductorWithMesos, self).setUp()
        self.baymodel_dict = {
            'image_id': 'image_id',
            'flavor_id': 'flavor_id',
            'master_flavor_id': 'master_flavor_id',
            'keypair_id': 'keypair_id',
            'dns_nameserver': 'dns_nameserver',
            'external_network_id': 'external_network_id',
            'fixed_network': '10.2.0.0/22',
            'cluster_distro': 'ubuntu',
            'coe': 'mesos',
            'http_proxy': 'http_proxy',
            'https_proxy': 'https_proxy',
            'no_proxy': 'no_proxy'
        }
        self.bay_dict = {
            'id': 1,
            'uuid': 'some_uuid',
            'baymodel_id': 'xx-xx-xx-xx',
            'name': 'bay1',
            'stack_id': 'xx-xx-xx-xx',
            'api_address': '172.17.2.3',
            'node_addresses': ['172.17.2.4'],
            'node_count': 1,
        }

    @patch('magnum.objects.BayModel.get_by_uuid')
    def test_extract_template_definition_all_values(
            self,
            mock_objects_baymodel_get_by_uuid):
        baymodel = objects.BayModel(self.context, **self.baymodel_dict)
        mock_objects_baymodel_get_by_uuid.return_value = baymodel
        bay = objects.Bay(self.context, **self.bay_dict)

        (template_path,
         definition) = bay_conductor._extract_template_definition(self.context,
                                                                  bay)

        expected = {
            'ssh_key_name': 'keypair_id',
            'external_network': 'external_network_id',
            'dns_nameserver': 'dns_nameserver',
            'server_image': 'image_id',
            'master_flavor': 'master_flavor_id',
            'slave_flavor': 'flavor_id',
            'number_of_slaves': '1',
            'fixed_network_cidr': '10.2.0.0/22',
            'http_proxy': 'http_proxy',
            'https_proxy': 'https_proxy',
            'no_proxy': 'no_proxy'
        }
        self.assertEqual(expected, definition)

    @patch('magnum.objects.BayModel.get_by_uuid')
    def test_extract_template_definition_only_required(
            self,
            mock_objects_baymodel_get_by_uuid):
        not_required = ['image_id', 'master_flavor_id', 'flavor_id',
                        'dns_nameserver', 'fixed_network', 'http_proxy',
                        'https_proxy', 'no_proxy']
        for key in not_required:
            self.baymodel_dict[key] = None

        baymodel = objects.BayModel(self.context, **self.baymodel_dict)
        mock_objects_baymodel_get_by_uuid.return_value = baymodel
        bay = objects.Bay(self.context, **self.bay_dict)

        (template_path,
         definition) = bay_conductor._extract_template_definition(self.context,
                                                                  bay)

        expected = {
            'ssh_key_name': 'keypair_id',
            'external_network': 'external_network_id',
            'number_of_slaves': '1',
        }
        self.assertEqual(expected, definition)

    @patch('magnum.conductor.utils.retrieve_baymodel')
    @patch('oslo_config.cfg')
    @patch('magnum.common.clients.OpenStackClients')
    def setup_poll_test(self, mock_openstack_client, cfg,
                        mock_retrieve_baymodel):
        cfg.CONF.bay_heat.max_attempts = 10
        bay = mock.MagicMock()
        mock_heat_stack = mock.MagicMock()
        mock_heat_client = mock.MagicMock()
        mock_heat_client.stacks.get.return_value = mock_heat_stack
        mock_openstack_client.heat.return_value = mock_heat_client
        baymodel = objects.BayModel(self.context, **self.baymodel_dict)
        mock_retrieve_baymodel.return_value = baymodel
        poller = bay_conductor.HeatPoller(mock_openstack_client, bay)
        return (mock_heat_stack, bay, poller)

    def test_poll_node_count(self):
        mock_heat_stack, bay, poller = self.setup_poll_test()

        mock_heat_stack.parameters = {'number_of_slaves': 1}
        mock_heat_stack.stack_status = bay_status.CREATE_IN_PROGRESS
        poller.poll_and_check()

        self.assertEqual(bay.node_count, 1)

    def test_poll_node_count_by_update(self):
        mock_heat_stack, bay, poller = self.setup_poll_test()

        mock_heat_stack.parameters = {'number_of_slaves': 2}
        mock_heat_stack.stack_status = bay_status.UPDATE_COMPLETE
        self.assertRaises(loopingcall.LoopingCallDone, poller.poll_and_check)

        self.assertEqual(bay.node_count, 2)
