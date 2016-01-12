# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.


from tempest_lib import exceptions
import testtools
import unittest

from magnum.tests.functional.common import base


class MagnumServiceTest(base.BaseMagnumTest):

    """Tests for magnum-service ."""

    def __init__(self, *args, **kwargs):
        super(MagnumServiceTest, self).__init__(*args, **kwargs)
        self.service_client = None

    # NOTE(suro-patz): The following test fails in lieu of non-admin user
    #                  available for functional-test-gate.
    #                  For now, I will keep the test, but skipped.
    @unittest.skip("Requires non-admin user in functional-test-gate")
    @testtools.testcase.attr('negative')
    def test_magnum_service_list_needs_admin(self):
        # Ensure that policy enforcement does not allow 'default' user
        (self.service_client, _) = self.get_clients_with_new_creds(
            type_of_creds='default',
            request_type='service')
        self.assertRaises(exceptions.ServerFault,
                          self.service_client.magnum_service_list)

    @testtools.testcase.attr('positive')
    def test_magnum_service_list(self):
        # get json object
        (self.service_client, _) = self.get_clients_with_new_creds(
            type_of_creds='admin',
            request_type='service')
        resp, msvcs = self.service_client.magnum_service_list()
        self.assertEqual(200, resp.status)
        # Note(suro-patz): Following code assumes that we have only
        #                  one service, magnum-conductor enabled, as of now.
        self.assertEqual(1, len(msvcs.mservices))
        mcond_svc = msvcs.mservices[0]
        self.assertEqual(mcond_svc['id'], 1)
        self.assertEqual('up', mcond_svc['state'])
        self.assertEqual('magnum-conductor', mcond_svc['binary'])
        self.assertGreater(mcond_svc['report_count'], 0)
