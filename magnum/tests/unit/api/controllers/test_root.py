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

import mock
from oslo_config import cfg
from webob import exc as webob_exc

import webtest

from magnum.api import app
from magnum.api.controllers import v1 as v1_api
from magnum.tests import base as test_base
from magnum.tests.unit.api import base as api_base


class TestRootController(api_base.FunctionalTest):
    def setUp(self):
        super(TestRootController, self).setUp()
        self.root_expected = {
            u'default_version':
            {u'id': u'v1', u'links':
             [{u'href': u'http://localhost/v1/', u'rel': u'self'}]},
            u'description': u'Magnum is an OpenStack project which '
            'aims to provide container management.',
            u'name': u'OpenStack Magnum API',
            u'versions': [{u'id': u'v1',
                          u'links':
                              [{u'href': u'http://localhost/v1/',
                                u'rel': u'self'}]}]}

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
            u'bays': [{u'href': u'http://localhost/v1/bays/',
                       u'rel': u'self'},
                      {u'href': u'http://localhost/bays/',
                       u'rel': u'bookmark'}],
            u'services': [{u'href': u'http://localhost/v1/services/',
                           u'rel': u'self'},
                          {u'href': u'http://localhost/services/',
                           u'rel': u'bookmark'}],
            u'baymodels': [{u'href': u'http://localhost/v1/baymodels/',
                            u'rel': u'self'},
                           {u'href': u'http://localhost/baymodels/',
                            u'rel': u'bookmark'}],
            u'pods': [{u'href': u'http://localhost/v1/pods/',
                       u'rel': u'self'},
                      {u'href': u'http://localhost/pods/',
                       u'rel': u'bookmark'}],
            u'rcs': [{u'href': u'http://localhost/v1/rcs/',
                      u'rel': u'self'},
                     {u'href': u'http://localhost/rcs/',
                      u'rel': u'bookmark'}],
            u'id': u'v1',
            u'containers': [{u'href': u'http://localhost/v1/containers/',
                             u'rel': u'self'},
                            {u'href': u'http://localhost/containers/',
                             u'rel': u'bookmark'}],
            u'x509keypairs': [{u'href': u'http://localhost/v1/x509keypairs/',
                               u'rel': u'self'},
                              {u'href': u'http://localhost/x509keypairs/',
                               u'rel': u'bookmark'}],
            u'certificates': [{u'href': u'http://localhost/v1/certificates/',
                               u'rel': u'self'},
                              {u'href': u'http://localhost/certificates/',
                               u'rel': u'bookmark'}],
            u'mservices': [{u'href': u'http://localhost/v1/mservices/',
                            u'rel': u'self'},
                           {u'href': u'http://localhost/mservices/',
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

    def test_noauth(self):
        # Don't need to auth
        paste_file = "magnum/tests/unit/api/controllers/noauth-paste.ini"
        app = self.make_app(paste_file)

        response = app.get('/')
        self.assertEqual(self.root_expected, response.json)

        response = app.get('/v1/')
        self.assertEqual(self.v1_expected, response.json)

        response = app.get('/v1/baymodels')
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

        response = app.get('/v1/baymodels', expect_errors=True)
        self.assertEqual(401, response.status_int)

    def test_auth_with_v1_access(self):
        # Only /v1 can access without auth
        paste_file = "magnum/tests/unit/api/controllers/auth-v1-access.ini"
        app = self.make_app(paste_file)

        response = app.get('/', expect_errors=True)
        self.assertEqual(401, response.status_int)

        response = app.get('/v1/')
        self.assertEqual(self.v1_expected, response.json)

        response = app.get('/v1/baymodels', expect_errors=True)
        self.assertEqual(401, response.status_int)


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
