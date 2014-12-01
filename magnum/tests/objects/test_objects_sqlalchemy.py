# Copyright 2013 - Red Hat, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
test_objects
----------------------------------

Tests for the sqlalchemy magnum 'objects' implementation
"""

import datetime
import uuid

import testtools
from testtools import matchers

from magnum.common import exception
from magnum import objects
from magnum.tests import base as tests
from magnum.tests import utils


class TestObjectsSqlalchemy(tests.BaseTestCase):
    def setUp(self):
        super(tests.BaseTestCase, self).setUp()
        self.ctx = utils.dummy_context()
        self.useFixture(utils.Database())

    def test_objects_reloadable(self):
        self.assertIsNotNone(objects.registry.Container)

        objects.registry.clear()

        with testtools.ExpectedException(KeyError):
            objects.registry.Container

        objects.load()

        self.assertIsNotNone(objects.registry.Container)

    def test_object_creatable(self):
        container = objects.registry.Container()
        self.assertIsNotNone(container)
        self.assertIsNone(container.id)

    def test_object_raises_not_found(self):
        with testtools.ExpectedException(exception.ResourceNotFound):
            objects.registry.Container.get_by_id(None, 10000)

    def test_object_persist_and_retrieve(self):
        container = objects.registry.Container()
        self.assertIsNotNone(container)
        container.uuid = str(uuid.uuid4())
        container.name = 'abc'
        container.image = 'ubuntu:latest'
        container.command = ['echo', 'hello world!']
        container.create(self.ctx)
        self.assertIsNotNone(container.id)

        container2 = objects.registry.Container.get_by_id(None, container.id)
        self.assertIsNotNone(container2)
        self.assertEqual(container.id, container2.id)
        self.assertEqual(container.uuid, container2.uuid)
        self.assertEqual(container.image, container2.image)
        self.assertEqual(container.command, container2.command)

        # visible via direct query
        dsession = utils.get_dummy_session()
        query = dsession.query(container.__class__).filter_by(id=container.id)
        container3 = query.first()
        self.assertIsNotNone(container3)
        self.assertEqual(container3.id, container3.id)

        # visible via get_all
        containers = objects.registry.ContainerList.get_all(None)
        exists = [item for item in containers if item.id == container.id]
        self.assertTrue(len(exists) > 0)

    def test_object_mutate(self):
        begin = datetime.datetime.utcnow()

        container = objects.registry.Container()
        self.assertIsNotNone(container)
        container.uuid = str(uuid.uuid4())
        container.image = 'ubuntu:latest'
        container.create(self.ctx)

        self.assertIsNotNone(container.id)
        self.assertThat(container.created_at, matchers.GreaterThan(begin))
        self.assertIsNone(container.updated_at)

        next_time = datetime.datetime.utcnow()

        container.save(self.ctx)

        self.assertThat(next_time, matchers.GreaterThan(container.created_at))
