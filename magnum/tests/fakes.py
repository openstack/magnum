# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import time
from unittest import mock

from oslo_service import loopingcall

fakeAuthTokenHeaders = {'X-User-Id': u'773a902f022949619b5c2f32cd89d419',
                        'X-Project-Id': u'5588aebbcdc24e17a061595f80574376',
                        'X-Project-Name': 'test',
                        'X-User-Name': 'test',
                        'X-Auth-Token': u'5588aebbcdc24e17a061595f80574376',
                        'X-Forwarded-For': u'10.10.10.10, 11.11.11.11',
                        'X-Service-Catalog': u'{test: 12345}',
                        'X-Roles': 'role1,role2',
                        'X-Auth-Url': 'fake_auth_url',
                        'X-Identity-Status': 'Confirmed',
                        'X-User-Domain-Name': 'domain',
                        'X-Project-Domain-Id': 'project_domain_id',
                        'X-User-Domain-Id': 'user_domain_id',
                        'OpenStack-API-Version': 'container-infra 1.0'
                        }


class FakePecanRequest(mock.Mock):

    def __init__(self, **kwargs):
        super(FakePecanRequest, self).__init__(**kwargs)
        self.host_url = 'http://test_url:8080/test'
        self.context = {}
        self.body = ''
        self.content_type = 'text/unicode'
        self.params = {}
        self.path = '/v1/services'
        self.headers = fakeAuthTokenHeaders
        self.environ = {}
        self.version = (1, 0)

    def __setitem__(self, index, value):
        setattr(self, index, value)


class FakePecanResponse(mock.Mock):

    def __init__(self, **kwargs):
        super(FakePecanResponse, self).__init__(**kwargs)
        self.status = None


class FakeApp(object):
    pass


class FakeService(mock.Mock):
    def __init__(self, **kwargs):
        super(FakeService, self).__init__(**kwargs)
        self.__tablename__ = 'service'
        self.__resource__ = 'services'
        self.user_id = 'fake user id'
        self.project_id = 'fake project id'
        self.uuid = 'test_uuid'
        self.id = 8
        self.name = 'james'
        self.service_type = 'not_this'
        self.description = 'amazing'
        self.tags = ['this', 'and that']
        self.read_only = True

    def as_dict(self):
        return dict(service_type=self.service_type,
                    user_id=self.user_id,
                    project_id=self.project_id,
                    uuid=self.uuid,
                    id=self.id,
                    name=self.name,
                    tags=self.tags,
                    read_only=self.read_only,
                    description=self.description)


class FakeAuthProtocol(mock.Mock):

    def __init__(self, **kwargs):
        super(FakeAuthProtocol, self).__init__(**kwargs)
        self.app = FakeApp()
        self.config = ''


class FakeLoopingCall(object):
    """Fake a looping call without the eventlet stuff

       For tests, just do a simple implementation so that we can ensure the
       called logic works rather than testing LoopingCall
    """

    def __init__(self, **kwargs):
        func = kwargs.pop("f", None)
        if func is None:
            raise ValueError("Must pass a callable in the -f kwarg.")
        self.call_func = func

    def start(self, interval, **kwargs):
        initial_delay = kwargs.pop("initial_delay", 0)
        stop_on_exception = kwargs.pop("stop_on_exception", True)
        if initial_delay:
            time.sleep(initial_delay)
        while True:
            try:
                self.call_func()
            except loopingcall.LoopingCallDone:
                return 0
            except Exception as exc:
                if stop_on_exception:
                    raise exc
            if interval:
                time.sleep(interval)
