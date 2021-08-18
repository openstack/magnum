# Licensed under the Apache License, Version 2.0 (the "License");
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

from unittest import mock

import fixtures
from oslo_config import cfg
from webob import exc as webob_exc

try:
    import configparser as ConfigParser
except ImportError:
    import ConfigParser
import shutil
import webtest

from magnum.api import app
from magnum.api.controllers import v1 as v1_api
from magnum.tests import base as test_base
from magnum.tests.unit.api import base as api_base


class TestRootController(api_base.FunctionalTest):
    def setUp(self):
        super(TestRootController, self).setUp()
        self.root_expected = {
            u'description': u'Magnum is an OpenStack project which '
                            'aims to provide container cluster management.',
            u'name': u'OpenStack Magnum API',
            u'versions': [{u'id': u'v1',
                           u'links':
                               [{u'href': u'http://localhost/v1/',
                                 u'rel': u'self'}],
                           u'status': u'CURRENT',
                           u'max_version': u'1.10',
                           u'min_version': u'1.1'}]}

        self.v1_expected = {
            u'media_types':
                [{u'base': u'application/json',
                  u'type': u'application/vnd.openstack.magnum.v1+json'}],
            u'links': [{u'href': u'http://localhost/v1/',
                        u'rel': u'self'},
                       {u'href':
                        u'http://docs.openstack.org/developer'
                        '/magnum/dev/api-spec-v1.html',
                        u'type': u'text/html', u'rel': u'describedby'}],
            u'stats': [{u'href': u'http://localhost/v1/stats/',
                       u'rel': u'self'},
                       {u'href': u'http://localhost/stats/',
                        u'rel': u'bookmark'}],
            u'bays': [{u'href': u'http://localhost/v1/bays/',
                       u'rel': u'self'},
                      {u'href': u'http://localhost/bays/',
                       u'rel': u'bookmark'}],
            u'baymodels': [{u'href': u'http://localhost/v1/baymodels/',
                            u'rel': u'self'},
                           {u'href': u'http://localhost/baymodels/',
                            u'rel': u'bookmark'}],
            u'clusters': [{u'href': u'http://localhost/v1/clusters/',
                           u'rel': u'self'},
                          {u'href': u'http://localhost/clusters/',
                           u'rel': u'bookmark'}],
            u'quotas': [{u'href': u'http://localhost/v1/quotas/',
                         u'rel': u'self'},
                        {u'href': u'http://localhost/quotas/',
                         u'rel': u'bookmark'}],
            u'clustertemplates':
                [{u'href': u'http://localhost/v1/clustertemplates/',
                  u'rel': u'self'},
                 {u'href': u'http://localhost/clustertemplates/',
                  u'rel': u'bookmark'}],
            u'id': u'v1',
            u'certificates': [{u'href': u'http://localhost/v1/certificates/',
                               u'rel': u'self'},
                              {u'href': u'http://localhost/certificates/',
                               u'rel': u'bookmark'}],
            u'mservices': [{u'href': u'http://localhost/v1/mservices/',
                            u'rel': u'self'},
                           {u'href': u'http://localhost/mservices/',
                            u'rel': u'bookmark'}],
            u'federations': [{u'href': u'http://localhost/v1/federations/',
                              u'rel': u'self'},
                             {u'href': u'http://localhost/federations/',
                              u'rel': u'bookmark'}],
            u'nodegroups': [{u'href': u'http://localhost/v1/clusters/'
                                      '{cluster_id}/nodegroups',
                             u'rel': u'self'},
                            {u'href': u'http://localhost/clusters/'
                                      '{cluster_id}/nodegroups',
                             u'rel': u'bookmark'}]}

    def make_app(self, paste_file):
        file_name = self.get_path(paste_file)
        cfg.CONF.set_override("api_paste_config", file_name, group="api")
        return webtest.TestApp(app.load_app())

    def test_version(self):
        response = self.app.get('/')
        self.assertEqual(self.root_expected, response.json)

    def test_v1_controller(self):
        response = self.app.get('/v1/')
        self.assertEqual(self.v1_expected, response.json)

    def test_get_not_found(self):
        response = self.app.get('/a/bogus/url', expect_errors=True)
        assert response.status_int == 404

    def test_api_paste_file_not_exist(self):
        cfg.CONF.set_override('api_paste_config', 'non-existent-file',
                              group='api')
        with mock.patch.object(cfg.CONF, 'find_file') as ff:
            ff.return_value = None
            self.assertRaises(cfg.ConfigFilesNotFoundError, app.load_app)

    @mock.patch('magnum.api.app.deploy')
    def test_api_paste_file_not_exist_not_abs(self, mock_deploy):
        path = self.get_path(cfg.CONF['api']['api_paste_config'] + 'test')
        cfg.CONF.set_override('api_paste_config', path, group='api')
        self.assertRaises(cfg.ConfigFilesNotFoundError, app.load_app)

    def test_noauth(self):
        # Don't need to auth
        paste_file = "magnum/tests/unit/api/controllers/noauth-paste.ini"
        app = self.make_app(paste_file)

        response = app.get('/')
        self.assertEqual(self.root_expected, response.json)

        response = app.get('/v1/')
        self.assertEqual(self.v1_expected, response.json)

        response = app.get('/v1/clustertemplates')
        self.assertEqual(200, response.status_int)

    def test_auth_with_no_public_routes(self):
        # All apis need auth when access
        paste_file = "magnum/tests/unit/api/controllers/auth-paste.ini"
        app = self.make_app(paste_file)

        response = app.get('/', expect_errors=True)
        self.assertEqual(401, response.status_int)

        response = app.get('/v1/', expect_errors=True)
        self.assertEqual(401, response.status_int)

    def test_auth_with_root_access(self):
        # Only / can access without auth
        paste_file = "magnum/tests/unit/api/controllers/auth-root-access.ini"
        app = self.make_app(paste_file)

        response = app.get('/')
        self.assertEqual(self.root_expected, response.json)

        response = app.get('/v1/', expect_errors=True)
        self.assertEqual(401, response.status_int)

        response = app.get('/v1/clustermodels', expect_errors=True)
        self.assertEqual(401, response.status_int)

    def test_auth_with_v1_access(self):
        # Only /v1 can access without auth
        paste_file = "magnum/tests/unit/api/controllers/auth-v1-access.ini"
        app = self.make_app(paste_file)

        response = app.get('/', expect_errors=True)
        self.assertEqual(401, response.status_int)

        response = app.get('/v1/')
        self.assertEqual(self.v1_expected, response.json)

        response = app.get('/v1/clustertemplates', expect_errors=True)
        self.assertEqual(401, response.status_int)


class TestHeathcheck(api_base.FunctionalTest):
    def setUp(self):
        self.addCleanup(self.remove_files)
        super(TestHeathcheck, self).setUp()

        # Create Temporary file
        self.tempdir = self.useFixture(fixtures.TempDir()).path
        paste_ini = "magnum/tests/unit/api/controllers/auth-paste.ini"

        # Read current file and create new one
        config = ConfigParser.RawConfigParser()
        config.read(self.get_path(paste_ini))
        config.set('app:healthcheck',
                   'disable_by_file_path',
                   self.tempdir + "/disable")
        with open(self.tempdir + "/paste.ini", 'wt') as configfile:
            config.write(configfile)

        # Set config and create app
        cfg.CONF.set_override("api_paste_config",
                              self.tempdir + "/paste.ini",
                              group="api")
        self.app = webtest.TestApp(app.load_app())

    def remove_files(self):
        shutil.rmtree(self.tempdir, ignore_errors=True)

    def test_healthcheck_enabled(self):
        # Check the healthcheck works
        response = self.app.get('/healthcheck')
        self.assertEqual(200, response.status_int)
        self.assertEqual(b"OK", response.body)

    def test_healthcheck_disable_file(self):
        # Create the file that disables healthcheck
        fo = open(self.tempdir + "/disable", 'a')
        fo.close()

        response = self.app.get('/healthcheck', expect_errors=True)
        self.assertEqual(503, response.status_int)
        self.assertEqual(b"DISABLED BY FILE", response.body)


class TestV1Routing(api_base.FunctionalTest):
    def test_route_checks_version(self):
        self.get_json('/')
        self._check_version.assert_called_once_with(mock.ANY,
                                                    mock.ANY)


class TestCheckVersions(test_base.TestCase):
    def setUp(self):
        super(TestCheckVersions, self).setUp()

        class ver(object):
            major = None
            minor = None

        self.version = ver()

    def test_check_version_invalid_major_version(self):
        self.version.major = v1_api.BASE_VERSION + 1
        self.version.minor = v1_api.MIN_VER.minor
        self.assertRaises(webob_exc.HTTPNotAcceptable,
                          v1_api.Controller()._check_version,
                          self.version)

    def test_check_version_too_low(self):
        self.version.major = v1_api.BASE_VERSION
        self.version.minor = v1_api.MIN_VER.minor - 1
        self.assertRaises(webob_exc.HTTPNotAcceptable,
                          v1_api.Controller()._check_version,
                          self.version)

    def test_check_version_too_high(self):
        self.version.major = v1_api.BASE_VERSION
        self.version.minor = v1_api.MAX_VER.minor + 1
        e = self.assertRaises(webob_exc.HTTPNotAcceptable,
                              v1_api.Controller()._check_version,
                              self.version, {'fake-headers':
                                             v1_api.MAX_VER.minor})

        self.assertEqual(v1_api.MAX_VER.minor, e.headers['fake-headers'])

    def test_check_version_ok(self):
        self.version.major = v1_api.BASE_VERSION
        self.version.minor = v1_api.MIN_VER.minor
        v1_api.Controller()._check_version(self.version)
