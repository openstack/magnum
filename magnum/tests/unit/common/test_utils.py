# Copyright 2011 Justin Santa Barbara
# Copyright 2012 Hewlett-Packard Development Company, L.P.
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

import errno
import os
import os.path
import shutil
import tempfile
from unittest import mock

from oslo_concurrency import processutils
from oslo_utils import netutils

from magnum.common import exception
from magnum.common import utils
import magnum.conf
from magnum.tests import base

CONF = magnum.conf.CONF


class UtilsTestCase(base.TestCase):

    def test_get_k8s_quantity(self):
        self.assertEqual(1024000.0, utils.get_k8s_quantity('1000Ki'))
        self.assertEqual(0.001, utils.get_k8s_quantity('1E-3'))
        self.assertEqual(0.5, utils.get_k8s_quantity('0.0005k'))
        self.assertEqual(0.5, utils.get_k8s_quantity('500m'))
        self.assertEqual(1300000.0, utils.get_k8s_quantity('1.3E+6'))
        self.assertEqual(1300000.0, utils.get_k8s_quantity('1.3E6'))
        self.assertRaises(exception.UnsupportedK8sQuantityFormat,
                          utils.get_k8s_quantity, '1E1E')

    def test_get_openstasck_ca(self):
        # openstack_ca_file is empty
        self.assertEqual('', utils.get_openstack_ca())

        # openstack_ca_file is set but the file doesn't exist
        CONF.set_override('openstack_ca_file',
                          '/tmp/invalid-ca.pem',
                          group='drivers')
        self.assertRaises(IOError, utils.get_openstack_ca)

        # openstack_ca_file is set and the file exists
        CONF.set_override('openstack_ca_file',
                          '/tmp/invalid-ca.pem',
                          group='drivers')
        with mock.patch('magnum.common.utils.open',
                        mock.mock_open(read_data="CERT"), create=True):
            self.assertEqual('CERT', utils.get_openstack_ca())


class ExecuteTestCase(base.TestCase):

    def test_retry_on_failure(self):
        fd, tmpfilename = tempfile.mkstemp()
        _, tmpfilename2 = tempfile.mkstemp()
        try:
            fp = os.fdopen(fd, 'w+')
            fp.write('''#!/bin/sh
# If stdin fails to get passed during one of the runs, make a note.
if ! grep -q foo
then
    echo 'failure' > "$1"
fi
# If stdin has failed to get passed during this or a previous run, exit early.
if grep failure "$1"
then
    exit 1
fi
runs="$(cat $1)"
if [ -z "$runs" ]
then
    runs=0
fi
runs=$(($runs + 1))
echo $runs > "$1"
exit 1
''')
            fp.close()
            os.chmod(tmpfilename, 0o755)
            try:
                self.assertRaises(processutils.ProcessExecutionError,
                                  utils.execute,
                                  tmpfilename, tmpfilename2, attempts=10,
                                  process_input=b'foo',
                                  delay_on_retry=False)
            except OSError as e:
                if e.errno == errno.EACCES:
                    self.skipTest("Permissions error detected. "
                                  "Are you running with a noexec /tmp?")
                else:
                    raise
            with open(tmpfilename2, 'r') as fp:
                runs = fp.read()
            self.assertNotEqual(runs.strip(), 'failure', 'stdin did not '
                                'always get passed '
                                'correctly')
            runs = int(runs.strip())
            self.assertEqual(10, runs,
                             'Ran %d times instead of 10.' % runs)
        finally:
            os.unlink(tmpfilename)
            os.unlink(tmpfilename2)

    def test_unknown_kwargs_raises_error(self):
        self.assertRaises(processutils.UnknownArgumentError,
                          utils.execute,
                          '/usr/bin/env', 'true',
                          this_is_not_a_valid_kwarg=True)

    def test_check_exit_code_boolean(self):
        utils.execute('/usr/bin/env', 'false', check_exit_code=False)
        self.assertRaises(processutils.ProcessExecutionError,
                          utils.execute,
                          '/usr/bin/env', 'false', check_exit_code=True)

    def test_no_retry_on_success(self):
        fd, tmpfilename = tempfile.mkstemp()
        _, tmpfilename2 = tempfile.mkstemp()
        try:
            fp = os.fdopen(fd, 'w+')
            fp.write('''#!/bin/sh
# If we've already run, bail out.
grep -q foo "$1" && exit 1
# Mark that we've run before.
echo foo > "$1"
# Check that stdin gets passed correctly.
grep foo
''')
            fp.close()
            os.chmod(tmpfilename, 0o755)
            try:
                utils.execute(tmpfilename,
                              tmpfilename2,
                              process_input=b'foo',
                              attempts=2)
            except OSError as e:
                if e.errno == errno.EACCES:
                    self.skipTest("Permissions error detected. "
                                  "Are you running with a noexec /tmp?")
                else:
                    raise
        finally:
            os.unlink(tmpfilename)
            os.unlink(tmpfilename2)

    @mock.patch.object(processutils, 'execute')
    @mock.patch.object(os.environ, 'copy', return_value={})
    def test_execute_use_standard_locale_no_env_variables(self, env_mock,
                                                          execute_mock):
        utils.execute('foo', use_standard_locale=True)
        execute_mock.assert_called_once_with('foo',
                                             env_variables={'LC_ALL': 'C'})

    @mock.patch.object(processutils, 'execute')
    def test_execute_use_standard_locale_with_env_variables(self,
                                                            execute_mock):
        utils.execute('foo', use_standard_locale=True,
                      env_variables={'foo': 'bar'})
        execute_mock.assert_called_once_with('foo',
                                             env_variables={'LC_ALL': 'C',
                                                            'foo': 'bar'})

    @mock.patch.object(processutils, 'execute')
    def test_execute_not_use_standard_locale(self, execute_mock):
        utils.execute('foo', use_standard_locale=False,
                      env_variables={'foo': 'bar'})
        execute_mock.assert_called_once_with('foo',
                                             env_variables={'foo': 'bar'})

    def test_execute_get_root_helper(self):
        with mock.patch.object(processutils, 'execute') as execute_mock:
            helper = utils._get_root_helper()
            utils.execute('foo', run_as_root=True)
            execute_mock.assert_called_once_with('foo', run_as_root=True,
                                                 root_helper=helper)

    def test_execute_without_root_helper(self):
        with mock.patch.object(processutils, 'execute') as execute_mock:
            utils.execute('foo', run_as_root=False)
            execute_mock.assert_called_once_with('foo', run_as_root=False)

    def test_validate_and_normalize_mac(self):
        mac = 'AA:BB:CC:DD:EE:FF'
        with mock.patch.object(netutils, 'is_valid_mac') as m_mock:
            m_mock.return_value = True
            self.assertEqual(mac.lower(),
                             utils.validate_and_normalize_mac(mac))

    def test_validate_and_normalize_mac_invalid_format(self):
        with mock.patch.object(netutils, 'is_valid_mac') as m_mock:
            m_mock.return_value = False
            self.assertRaises(exception.InvalidMAC,
                              utils.validate_and_normalize_mac, 'invalid-mac')

    def test_safe_rstrip(self):
        value = '/test/'
        rstripped_value = '/test'
        not_rstripped = '/'

        self.assertEqual(rstripped_value, utils.safe_rstrip(value, '/'))
        self.assertEqual(not_rstripped, utils.safe_rstrip(not_rstripped, '/'))

    def test_safe_rstrip_not_raises_exceptions(self):
        # Supplying an integer should normally raise an exception because it
        # does not save the rstrip() method.
        value = 10

        # In the case of raising an exception safe_rstrip() should return the
        # original value.
        self.assertEqual(value, utils.safe_rstrip(value))


class TempFilesTestCase(base.TestCase):

    def test_tempdir(self):

        dirname = None
        with utils.tempdir() as tempdir:
            self.assertTrue(os.path.isdir(tempdir))
            dirname = tempdir
        self.assertFalse(os.path.exists(dirname))

    @mock.patch.object(shutil, 'rmtree')
    @mock.patch.object(tempfile, 'mkdtemp')
    def test_tempdir_mocked(self, mkdtemp_mock, rmtree_mock):

        self.config(tempdir='abc')
        mkdtemp_mock.return_value = 'temp-dir'
        kwargs = {'a': 'b'}

        with utils.tempdir(**kwargs) as tempdir:
            self.assertEqual('temp-dir', tempdir)
            tempdir_created = tempdir

        mkdtemp_mock.assert_called_once_with(**kwargs)
        rmtree_mock.assert_called_once_with(tempdir_created)

    @mock.patch.object(utils, 'LOG')
    @mock.patch.object(shutil, 'rmtree')
    @mock.patch.object(tempfile, 'mkdtemp')
    def test_tempdir_mocked_error_on_rmtree(self, mkdtemp_mock, rmtree_mock,
                                            log_mock):

        self.config(tempdir='abc')
        mkdtemp_mock.return_value = 'temp-dir'
        rmtree_mock.side_effect = OSError

        with utils.tempdir() as tempdir:
            self.assertEqual('temp-dir', tempdir)
            tempdir_created = tempdir

        rmtree_mock.assert_called_once_with(tempdir_created)
        self.assertTrue(log_mock.error.called)


class GeneratePasswordTestCase(base.TestCase):
    def test_generate_password(self):
        password = utils.generate_password(length=12)
        self.assertTrue([c for c in password if c in '0123456789'])
        self.assertTrue([c for c in password
                         if c in 'abcdefghijklmnopqrstuvwxyz'])
        self.assertTrue([c for c in password
                         if c in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'])
