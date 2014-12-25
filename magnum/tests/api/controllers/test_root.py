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
from magnum import tests


class TestRootController(tests.FunctionalTest):
    def test_version(self):
        expected = {u'default_version':
                    {u'id': u'v1', u'links':
                     [{u'href': u'http://localhost/v1/', u'rel': u'self'}]},
                    u'description': u'Magnum is an OpenStack project which '
                    'aims to provide container management.',
                    u'name': u'OpenStack Magnum API',
                    u'versions': [{u'id': u'v1',
                                  u'links':
                                      [{u'href': u'http://localhost/v1/',
                                        u'rel': u'self'}]}]}

        response = self.app.get('/')
        self.assertEqual(expected, response.json)

    def test_v1_controller(self):
        expected = {u'media_types':
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
                {u'href': u'http://localhost/bays/',
                u'rel': u'bookmark'}],
                u'pods': [{u'href': u'http://localhost/v1/pods/',
            u'rel': u'self'},
                {u'href': u'http://localhost/pods/',
                u'rel': u'bookmark'}],
                u'id': u'v1',
            u'containers': [{u'href': u'http://localhost/v1/containers/',
                u'rel': u'self'},
                {u'href': u'http://localhost/containers/',
                u'rel': u'bookmark'}]}

        response = self.app.get('/v1/')
        self.assertEqual(expected, response.json)

    def test_get_not_found(self):
        response = self.app.get('/a/bogus/url', expect_errors=True)
        assert response.status_int == 404
