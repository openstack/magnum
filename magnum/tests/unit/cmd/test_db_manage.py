# Copyright 2016 - Fujitsu, Ltd.
#
#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

import io
from unittest import mock

from magnum.cmd import db_manage
from magnum.tests import base


class TestMagnumDbManage(base.TestCase):

    def setUp(self):
        super(TestMagnumDbManage, self).setUp()

        def clear_conf():
            db_manage.CONF.reset()
            db_manage.CONF.unregister_opt(db_manage.command_opt)

        clear_conf()
        self.addCleanup(clear_conf)

    @mock.patch('magnum.db.migration.version')
    @mock.patch('sys.argv', ['magnum-db-manage', 'version'])
    def test_db_manage_version(self, mock_version):
        with mock.patch('sys.stdout', new=io.StringIO()) as fakeOutput:
            mock_version.return_value = '123456'
            db_manage.main()
            self.assertEqual('Current DB revision is 123456\n',
                             fakeOutput.getvalue())
            mock_version.assert_called_once_with()

    @mock.patch('magnum.db.migration.upgrade')
    @mock.patch('sys.argv', ['magnum-db-manage', 'upgrade'])
    def test_db_manage_upgrade(self, mock_upgrade):
        db_manage.main()
        mock_upgrade.assert_called_once_with(base.CONF.command.revision)

    @mock.patch('magnum.db.migration.stamp')
    @mock.patch('sys.argv', ['magnum-db-manage', 'stamp', 'foo bar'])
    def test_db_manage_stamp(self, mock_stamp):
        db_manage.main()
        mock_stamp.assert_called_once_with('foo bar')

    @mock.patch('magnum.db.migration.revision')
    @mock.patch('sys.argv', ['magnum-db-manage', 'revision', '-m', 'foo bar'])
    def test_db_manage_revision(self, mock_revision):
        db_manage.main()
        mock_revision.assert_called_once_with(
            message='foo bar',
            autogenerate=base.CONF.command.autogenerate)
