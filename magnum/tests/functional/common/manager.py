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

from tempest_lib import auth
from tempest_lib import exceptions

import magnum.tests.functional.common.config as config


class Manager(object):

    """Responsible for providing an auth provider object"""

    def _get_auth_credentials(self, auth_version, **credentials):
        """Retrieves auth credentials based on passed in creds and version

        :param auth_version: auth version ('v2' or 'v3')
        :param credentials: credentials dict to validate against
        :returns: credentials object
        """

        if credentials is None:
            raise exceptions.InvalidCredentials(
                'Credentials must be specified')
        if auth_version == 'v3':
            return auth.KeystoneV3Credentials(**credentials)
        elif auth_version == 'v2':
            return auth.KeystoneV2Credentials(**credentials)
        else:
            raise exceptions.InvalidCredentials('Specify identity version')

    def get_auth_provider(self, **credentials):
        """Validates credentials and returns auth provider

        Auth provider will contain required security context to pass to magnum

        :param credentials: credentials dict to validate against
        :returns: auth provider object
        """

        auth_version = config.Config.auth_version
        creds = self._get_auth_credentials(auth_version, **credentials)
        if auth_version == 'v3':
            auth_provider = auth.KeystoneV3AuthProvider(
                creds, config.Config.auth_url)
        elif auth_version == 'v2':
            auth_provider = auth.KeystoneV2AuthProvider(
                creds, config.Config.auth_url)
        else:
            raise exceptions.InvalidCredentials('Specify identity version')

        auth_provider.fill_credentials()
        return auth_provider
