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

from oslo_serialization import jsonutils
from webob import exc


class HTTPNotAcceptableAPIVersion(exc.HTTPNotAcceptable):
    # subclass of :class:`~HTTPNotAcceptable`
    #
    # This indicates the resource identified by the request is only
    # capable of generating response entities which have content
    # characteristics not acceptable according to the accept headers
    # sent in the request.
    #
    # code: 406, title: Not Acceptable
    #
    # differences from webob.exc.HTTPNotAcceptable:
    #
    # - additional max and min version parameters
    # - additional error info for code, title, and links
    code = 406
    title = 'Not Acceptable'
    max_version = ''
    min_version = ''

    def __init__(self, detail=None, headers=None, comment=None,
                 body_template=None, max_version='', min_version='', **kw):

        super(HTTPNotAcceptableAPIVersion, self).__init__(
            detail=detail, headers=headers, comment=comment,
            body_template=body_template, **kw)

        self.max_version = max_version
        self.min_version = min_version

    def __call__(self, environ, start_response):
        for err_str in self.app_iter:
            err = {}
            try:
                err = jsonutils.loads(err_str.decode('utf-8'))
            except ValueError:
                pass

            links = {'rel': 'help', 'href': 'http://docs.openstack.org'
                     '/api-guide/compute/microversions.html'}

            err['max_version'] = self.max_version
            err['min_version'] = self.min_version
            err['code'] = "magnum.microversion-unsupported"
            err['links'] = [links]
            err['title'] = "Requested microversion is unsupported"

        self.app_iter = [jsonutils.dump_as_bytes(err)]
        self.headers['Content-Length'] = str(len(self.app_iter[0]))

        return super(HTTPNotAcceptableAPIVersion, self).__call__(
            environ, start_response)
