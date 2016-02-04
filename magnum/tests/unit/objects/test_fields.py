# Copyright 2015 IBM Corp.
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

from oslo_versionedobjects.tests import test_fields

from magnum.objects import fields


class TestBayStatus(test_fields.TestField):
    def setUp(self):
        super(TestBayStatus, self).setUp()
        self.field = fields.BayStatusField()
        self.coerce_good_values = [('CREATE_IN_PROGRESS',
                                    'CREATE_IN_PROGRESS'),
                                   ('CREATE_FAILED', 'CREATE_FAILED'),
                                   ('CREATE_COMPLETE', 'CREATE_COMPLETE'),
                                   ('UPDATE_IN_PROGRESS',
                                    'UPDATE_IN_PROGRESS'),
                                   ('UPDATE_FAILED', 'UPDATE_FAILED'),
                                   ('UPDATE_COMPLETE', 'UPDATE_COMPLETE'),
                                   ('DELETE_IN_PROGRESS',
                                    'DELETE_IN_PROGRESS'),
                                   ('DELETE_FAILED', 'DELETE_FAILED'),
                                   ('RESUME_COMPLETE', 'RESUME_COMPLETE'),
                                   ('RESTORE_COMPLETE', 'RESTORE_COMPLETE'),
                                   ('ROLLBACK_COMPLETE', 'ROLLBACK_COMPLETE'),
                                   ('SNAPSHOT_COMPLETE', 'SNAPSHOT_COMPLETE'),
                                   ('CHECK_COMPLETE', 'CHECK_COMPLETE'),
                                   ('ADOPT_COMPLETE', 'ADOPT_COMPLETE')]
        self.coerce_bad_values = ['DELETE_STOPPED']
        self.to_primitive_values = self.coerce_good_values[0:1]
        self.from_primitive_values = self.coerce_good_values[0:1]

    def test_stringify(self):
        self.assertEqual("'UPDATE_FAILED'",
                         self.field.stringify('UPDATE_FAILED'))

    def test_stringify_invalid(self):
        self.assertRaises(ValueError, self.field.stringify, 'DELETE_STOPPED')


class TestContainerStatus(test_fields.TestField):
    def setUp(self):
        super(TestContainerStatus, self).setUp()
        self.field = fields.ContainerStatusField()
        self.coerce_good_values = [('Error', 'Error'), ('Running', 'Running'),
                                   ('Stopped', 'Stopped'),
                                   ('Paused', 'Paused'),
                                   ('Unknown', 'Unknown'), ]
        self.coerce_bad_values = ['DELETED']

        self.to_primitive_values = self.coerce_good_values[0:1]
        self.from_primitive_values = self.coerce_good_values[0:1]

    def test_stringify(self):
        self.assertEqual("'Stopped'",
                         self.field.stringify('Stopped'))

    def test_stringify_invalid(self):
        self.assertRaises(ValueError, self.field.stringify, 'DELETED')


class TestBayType(test_fields.TestField):
    def setUp(self):
        super(TestBayType, self).setUp()
        self.field = fields.BayTypeField()
        self.coerce_good_values = [('kubernetes', 'kubernetes'),
                                   ('swarm', 'swarm'),
                                   ('mesos', 'mesos'), ]
        self.coerce_bad_values = ['invalid']

        self.to_primitive_values = self.coerce_good_values[0:1]
        self.from_primitive_values = self.coerce_good_values[0:1]

    def test_stringify(self):
        self.assertEqual("'kubernetes'",
                         self.field.stringify('kubernetes'))

    def test_stringify_invalid(self):
        self.assertRaises(ValueError, self.field.stringify, 'invalid')
