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

from magnum import base


KEYSTONE_URL = "https://example.com:5000/v2.0/"


class NovaBayBase(base.BayBase):
    pass


class NovaBayFactory(NovaBayBase):
    def __init__(self):
        pass

    def list(self):
        self.nova.servers.list()

    def create(self, pod_definition=None):
        pass

    def get_pod(self, pod_id):
        return NovaBay(pod_id)


class NovaBay(NovaBayBase):
    def __init__(self, pod_id):
        self.pod_id = pod_id

    def destroy(self):
        pass

    def stop(self):
        pass
