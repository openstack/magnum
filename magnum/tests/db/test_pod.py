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

"""Tests for manipulating Pods via the DB API"""

import six

from magnum.common import exception
from magnum.common import utils as magnum_utils
from magnum.tests.db import base
from magnum.tests.db import utils as utils


class DbPodTestCase(base.DbTestCase):

    def setUp(self):
        # This method creates a pod for every test and
        # replaces a test for creating a pod.
        super(DbPodTestCase, self).setUp()
        self.bay = utils.create_test_bay()
        self.pod = utils.create_test_pod(bay_uuid=self.bay.uuid)

    def test_create_pod_duplicated_uuid(self):
        self.assertRaises(exception.PodAlreadyExists,
                          utils.create_test_pod,
                          uuid=self.pod.uuid,
                          bay_uuid=self.bay.uuid)

    def test_get_pod_by_id(self):
        res = self.dbapi.get_pod_by_id(self.context, self.pod.id)
        self.assertEqual(self.pod.id, res.id)
        self.assertEqual(self.pod.uuid, res.uuid)

    def test_get_pod_by_uuid(self):
        res = self.dbapi.get_pod_by_uuid(self.context, self.pod.uuid)
        self.assertEqual(self.pod.id, res.id)
        self.assertEqual(self.pod.uuid, res.uuid)

    def test_get_pod_by_name(self):
        res = self.dbapi.get_pod_by_name(self.pod.name)
        self.assertEqual(self.pod.id, res.id)
        self.assertEqual(self.pod.uuid, res.uuid)

    def test_get_pod_that_does_not_exist(self):
        self.assertRaises(exception.PodNotFound,
                          self.dbapi.get_pod_by_id, self.context, 999)
        self.assertRaises(exception.PodNotFound,
                          self.dbapi.get_pod_by_uuid,
                          self.context,
                          magnum_utils.generate_uuid())
        self.assertRaises(exception.PodNotFound,
                          self.dbapi.get_pod_by_name,
                          'bad-name')

    def test_get_podinfo_list_defaults(self):
        pod_id_list = [self.pod.id]
        for i in range(1, 6):
            pod = utils.create_test_pod(bay_uuid=self.bay.uuid,
                uuid=magnum_utils.generate_uuid())
            pod_id_list.append(pod.id)
        res = [i[0] for i in self.dbapi.get_podinfo_list()]
        self.assertEqual(sorted(res), sorted(pod_id_list))

    def test_get_podinfo_list_with_cols(self):
        uuids = {self.pod.id: self.pod.uuid}
        names = {self.pod.id: self.pod.name}
        for i in range(1, 6):
            uuid = magnum_utils.generate_uuid()
            name = 'pod' + str(i)
            pod = utils.create_test_pod(name=name, uuid=uuid,
                                        bay_uuid=self.bay.uuid)
            uuids[pod.id] = uuid
            names[pod.id] = name
        res = self.dbapi.get_podinfo_list(columns=['id', 'name', 'uuid'])
        self.assertEqual(names, dict((r[0], r[1]) for r in res))
        self.assertEqual(uuids, dict((r[0], r[2]) for r in res))

    def test_get_podinfo_list_with_filters(self):
        bay1 = utils.get_test_bay(id=11, uuid=magnum_utils.generate_uuid())
        bay2 = utils.get_test_bay(id=12, uuid=magnum_utils.generate_uuid())

        self.dbapi.create_bay(bay1)
        self.dbapi.create_bay(bay2)

        pod1 = utils.create_test_pod(name='pod-one',
            uuid=magnum_utils.generate_uuid(),
            bay_uuid=bay1['uuid'],
            status='status1')
        pod2 = utils.create_test_pod(name='pod-two',
            uuid=magnum_utils.generate_uuid(),
            bay_uuid=bay2['uuid'],
            status='status2')

        res = self.dbapi.get_podinfo_list(filters={'bay_uuid': bay1['uuid']})
        self.assertEqual([pod1.id], [r.id for r in res])

        res = self.dbapi.get_podinfo_list(filters={'bay_uuid': bay2['uuid']})
        self.assertEqual([pod2.id], [r.id for r in res])

        res = self.dbapi.get_podinfo_list(filters={'name': 'pod-one'})
        self.assertEqual([pod1.id], [r[0] for r in res])

        res = self.dbapi.get_podinfo_list(filters={'name': 'bad-pod'})
        self.assertEqual([], [r[0] for r in res])

        res = self.dbapi.get_podinfo_list(filters={'status': 'status1'})
        self.assertEqual([pod1.id], [r[0] for r in res])

        res = self.dbapi.get_podinfo_list(filters={'status': 'status2'})
        self.assertEqual([pod2.id], [r[0] for r in res])

    def test_get_pod_list(self):
        uuids = [self.pod.uuid]
        for i in range(1, 6):
            pod = utils.create_test_pod(uuid=magnum_utils.generate_uuid(),
                                        bay_uuid=self.bay.uuid)
            uuids.append(six.text_type(pod.uuid))
        res = self.dbapi.get_pod_list(self.context)
        res_uuids = [r.uuid for r in res]
        self.assertEqual(sorted(uuids), sorted(res_uuids))

    def test_get_pod_list_with_filters(self):
        bay1 = utils.get_test_bay(id=11, uuid=magnum_utils.generate_uuid())
        bay2 = utils.get_test_bay(id=12, uuid=magnum_utils.generate_uuid())
        self.dbapi.create_bay(bay1)
        self.dbapi.create_bay(bay2)

        pod1 = utils.create_test_pod(name='pod-one',
            uuid=magnum_utils.generate_uuid(),
            bay_uuid=bay1['uuid'],
            status='status1')
        pod2 = utils.create_test_pod(name='pod-two',
            uuid=magnum_utils.generate_uuid(),
            bay_uuid=bay2['uuid'],
            status='status2')

        res = self.dbapi.get_pod_list(self.context,
                                      filters={'bay_uuid': bay1['uuid']})
        self.assertEqual([pod1.id], [r.id for r in res])

        res = self.dbapi.get_pod_list(self.context,
                                      filters={'bay_uuid': bay2['uuid']})
        self.assertEqual([pod2.id], [r.id for r in res])

        res = self.dbapi.get_pod_list(self.context,
                                      filters={'name': 'pod-one'})
        self.assertEqual([pod1.id], [r.id for r in res])

        res = self.dbapi.get_pod_list(self.context,
                                      filters={'name': 'bad-pod'})
        self.assertEqual([], [r.id for r in res])

        res = self.dbapi.get_pod_list(self.context,
                                      filters={'status': 'status1'})
        self.assertEqual([pod1.id], [r.id for r in res])

        res = self.dbapi.get_pod_list(self.context,
                                      filters={'status': 'status2'})
        self.assertEqual([pod2.id], [r.id for r in res])

    def test_get_pod_list_bay_not_exist(self):
        res = self.dbapi.get_pod_list(self.context,
                                      {'bay_uuid': self.bay.uuid})
        self.assertEqual(1, len(res))
        res = self.dbapi.get_pod_list(self.context, {
            'bay_uuid': magnum_utils.generate_uuid()})
        self.assertEqual(0, len(res))

    def test_get_pods_by_bay_uuid(self):
        res = self.dbapi.get_pods_by_bay_uuid(self.bay.uuid)
        self.assertEqual(self.pod.id, res[0].id)

    def test_get_pods_by_bay_uuid_that_does_not_exist(self):
        res = self.dbapi.get_pods_by_bay_uuid(magnum_utils.generate_uuid())
        self.assertEqual([], res)

    def test_destroy_pod(self):
        self.dbapi.destroy_pod(self.pod.id)
        self.assertRaises(exception.PodNotFound,
                          self.dbapi.get_pod_by_id, self.context, self.pod.id)

    def test_destroy_pod_by_uuid(self):
        self.assertIsNotNone(self.dbapi.get_pod_by_uuid(self.context,
                                                        self.pod.uuid))
        self.dbapi.destroy_pod(self.pod.uuid)
        self.assertRaises(exception.PodNotFound,
                          self.dbapi.get_pod_by_uuid,
                          self.context, self.pod.uuid)

    def test_destroy_pod_that_does_not_exist(self):
        self.assertRaises(exception.PodNotFound,
                          self.dbapi.destroy_pod,
                          magnum_utils.generate_uuid())

    def test_update_pod(self):
        old_name = self.pod.name
        new_name = 'new-pod'
        self.assertNotEqual(old_name, new_name)
        res = self.dbapi.update_pod(self.pod.id, {'name': new_name})
        self.assertEqual(new_name, res.name)

    def test_update_pod_not_found(self):
        pod_uuid = magnum_utils.generate_uuid()
        self.assertRaises(exception.PodNotFound, self.dbapi.update_pod,
                          pod_uuid, {'status': 'Running'})

    def test_update_pod_uuid(self):
        self.assertRaises(exception.InvalidParameterValue,
                          self.dbapi.update_pod, self.pod.id,
                          {'uuid': ''})
