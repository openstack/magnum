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


from webob import exc

from magnum.i18n import _

#
# For each newly added microversion change, update the API version history
# string below with a one or two line description. Also update
# rest_api_version_history.rst for extra information on microversion.
REST_API_VERSION_HISTORY = """REST API Version History:

    * 1.1 - Initial version
    * 1.2 - Async bay operations support
    * 1.3 - Add bay rollback support
    * 1.4 - Add stats API
    * 1.5 - Add cluster CA certificate rotation support
    * 1.6 - Add quotas API
    * 1.7 - Add resize API
    * 1.8 - Add upgrade API
    * 1.9 - Add nodegroup API
    * 1.10 - Allow nodegroups with 0 nodes
    * 1.11 - Remove bay and baymodel objects
"""

BASE_VER = '1.1'
CURRENT_MAX_VER = '1.11'


class Version(object):
    """API Version object."""

    string = 'OpenStack-API-Version'
    """HTTP Header string carrying the requested version"""

    min_string = 'OpenStack-API-Minimum-Version'
    """HTTP response header"""

    max_string = 'OpenStack-API-Maximum-Version'
    """HTTP response header"""

    service_string = 'container-infra'

    def __init__(self, headers, default_version, latest_version,
                 from_string=None):
        """Create an API Version object from the supplied headers.

        :param headers: webob headers
        :param default_version: version to use if not specified in headers
        :param latest_version: version to use if latest is requested
        :param from_string: create the version from string not headers
        :raises: webob.HTTPNotAcceptable
        """
        if from_string:
            (self.major, self.minor) = tuple(int(i)
                                             for i in from_string.split('.'))

        else:
            (self.major, self.minor) = Version.parse_headers(headers,
                                                             default_version,
                                                             latest_version)

    def __repr__(self):
        return '%s.%s' % (self.major, self.minor)

    @staticmethod
    def parse_headers(headers, default_version, latest_version):
        """Determine the API version requested based on the headers supplied.

        :param headers: webob headers
        :param default_version: version to use if not specified in headers
        :param latest_version: version to use if latest is requested
        :returns: a tuple of (major, minor) version numbers
        :raises: webob.HTTPNotAcceptable
        """

        version_hdr = headers.get(Version.string, default_version)

        try:
            version_service, version_str = version_hdr.split()
        except ValueError:
            raise exc.HTTPNotAcceptable(_(
                "Invalid service type for %s header") % Version.string)

        if version_str.lower() == 'latest':
            version_service, version_str = latest_version.split()

        if version_service != Version.service_string:
            raise exc.HTTPNotAcceptable(_(
                "Invalid service type for %s header") % Version.string)
        try:
            version = tuple(int(i) for i in version_str.split('.'))
        except ValueError:
            version = ()

        if len(version) != 2:
            raise exc.HTTPNotAcceptable(_(
                "Invalid value for %s header") % Version.string)
        return version

    def is_null(self):
        return self.major == 0 and self.minor == 0

    def matches(self, start_version, end_version):
        if self.is_null():
            raise ValueError

        return start_version <= self <= end_version

    def __lt__(self, other):
        if self.major < other.major:
            return True
        if self.major == other.major and self.minor < other.minor:
            return True
        return False

    def __gt__(self, other):
        if self.major > other.major:
            return True
        if self.major == other.major and self.minor > other.minor:
            return True
        return False

    def __eq__(self, other):
        return self.major == other.major and self.minor == other.minor

    def __le__(self, other):
        return self < other or self == other

    def __ne__(self, other):
        return not self.__eq__(other)

    def __ge__(self, other):
        return self > other or self == other
