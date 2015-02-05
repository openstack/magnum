# Copyright 2015 OpenStack Foundation
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

import mock
from testtools.matchers import HasLength

from magnum.common import utils as magnum_utils
from magnum import objects
from magnum.tests.db import base
from magnum.tests.db import utils


class TestPodObject(base.DbTestCase):

    def setUp(self):
        super(TestPodObject, self).setUp()
        self.fake_pod = utils.get_test_pod()

    def test_get_by_id(self):
        pod_id = self.fake_pod['id']
        with mock.patch.object(self.dbapi, 'get_pod_by_id',
                               autospec=True) as mock_get_pod:
            mock_get_pod.return_value = self.fake_pod
            pod = objects.Pod.get_by_id(self.context, pod_id)
            mock_get_pod.assert_called_once_with(self.context, pod_id)
            self.assertEqual(self.context, pod._context)

    def test_get_by_uuid(self):
        uuid = self.fake_pod['uuid']
        with mock.patch.object(self.dbapi, 'get_pod_by_uuid',
                               autospec=True) as mock_get_pod:
            mock_get_pod.return_value = self.fake_pod
            pod = objects.Pod.get_by_uuid(self.context, uuid)
            mock_get_pod.assert_called_once_with(self.context, uuid)
            self.assertEqual(self.context, pod._context)

    def test_list(self):
        with mock.patch.object(self.dbapi, 'get_pod_list',
                               autospec=True) as mock_get_list:
            mock_get_list.return_value = [self.fake_pod]
            pods = objects.Pod.list(self.context)
            self.assertEqual(mock_get_list.call_count, 1)
            self.assertThat(pods, HasLength(1))
            self.assertIsInstance(pods[0], objects.Pod)
            self.assertEqual(self.context, pods[0]._context)

    def test_create(self):
        with mock.patch.object(self.dbapi, 'create_pod',
                               autospec=True) as mock_create_pod:
            mock_create_pod.return_value = self.fake_pod
            pod = objects.Pod(self.context, **self.fake_pod)
            pod.create()
            mock_create_pod.assert_called_once_with(self.fake_pod)
            self.assertEqual(self.context, pod._context)

    def test_destroy(self):
        uuid = self.fake_pod['uuid']
        with mock.patch.object(self.dbapi, 'get_pod_by_uuid',
                               autospec=True) as mock_get_pod:
            mock_get_pod.return_value = self.fake_pod
            with mock.patch.object(self.dbapi, 'destroy_pod',
                                   autospec=True) as mock_destroy_pod:
                pod = objects.Pod.get_by_uuid(self.context, uuid)
                pod.destroy()
                mock_get_pod.assert_called_once_with(self.context, uuid)
                mock_destroy_pod.assert_called_once_with(uuid)
                self.assertEqual(self.context, pod._context)

    def test_save(self):
        uuid = self.fake_pod['uuid']
        with mock.patch.object(self.dbapi, 'get_pod_by_uuid',
                               autospec=True) as mock_get_pod:
            mock_get_pod.return_value = self.fake_pod
            with mock.patch.object(self.dbapi, 'update_pod',
                                   autospec=True) as mock_update_pod:
                pod = objects.Pod.get_by_uuid(self.context, uuid)
                pod.desc = 'test-pod'
                pod.save()

                mock_get_pod.assert_called_once_with(self.context, uuid)
                mock_update_pod.assert_called_once_with(
                        uuid, {'desc': 'test-pod'})
                self.assertEqual(self.context, pod._context)

    def test_refresh(self):
        uuid = self.fake_pod['uuid']
        new_uuid = magnum_utils.generate_uuid()
        returns = [dict(self.fake_pod, uuid=uuid),
                   dict(self.fake_pod, uuid=new_uuid)]
        expected = [mock.call(self.context, uuid),
                    mock.call(self.context, uuid)]
        with mock.patch.object(self.dbapi, 'get_pod_by_uuid',
                               side_effect=returns,
                               autospec=True) as mock_get_pod:
            pod = objects.Pod.get_by_uuid(self.context, uuid)
            self.assertEqual(uuid, pod.uuid)
            pod.refresh()
            self.assertEqual(new_uuid, pod.uuid)
            self.assertEqual(expected, mock_get_pod.call_args_list)
            self.assertEqual(self.context, pod._context)
