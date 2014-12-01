#    Licensed under the Apache License, Version 2.0 (the "License");
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

import uuid

from pecan import rest
import wsme
from wsme import types as wtypes
import wsmeext.pecan as wsme_pecan

from magnum.api.controllers.v1.base import Base
from magnum.api.controllers.v1.base import Query

# NOTE(dims): We don't depend on oslo*i18n yet
_ = _LI = _LW = _LE = _LC = lambda x: x


class Pod(Base):
    id = wtypes.text
    """ The ID of the pods."""

    name = wsme.wsattr(wtypes.text, mandatory=True)
    """ The name of the pod."""

    desc = wsme.wsattr(wtypes.text, mandatory=True)

    def __init__(self, **kwargs):
        super(Pod, self).__init__(**kwargs)

    @classmethod
    def sample(cls):
        return cls(id=str(uuid.uuid1()),
                   name="Docker",
                   desc='Docker Pods')


class PodController(rest.RestController):
    """Manages Pods."""
    def __init__(self, **kwargs):
        super(PodController, self).__init__(**kwargs)

        self.pod_list = []

    @wsme_pecan.wsexpose(Pod, wtypes.text)
    def get_one(self, id):
        """Retrieve details about one pod.

        :param id: An ID of the pod.
        """
        for pod in self.pod_list:
            if pod.id == id:
                return pod
        return None

    @wsme_pecan.wsexpose([Pod], [Query], int)
    def get_all(self, q=None, limit=None):
        """Retrieve definitions of all of the pods.

        :param query: query parameters.
        :param limit: The number of pods to retrieve.
        """
        if len(self.pod_list) == 0:
            return []
        return self.pod_list

    @wsme_pecan.wsexpose(Pod, wtypes.text, wtypes.text)
    def post(self, name, desc):
        """Create a new pod.

        :param pod: a pod within the request body.
        """
        pod = Pod(id=str(uuid.uuid1()), name=name, desc=desc)
        self.pod_list.append(pod)

        return pod

    @wsme_pecan.wsexpose(Pod, wtypes.text, body=Pod)
    def put(self, id, pod):
        """Modify this pod.

        :param id: An ID of the pod.
        :param pod: a pod within the request body.
        """
        pass

    @wsme_pecan.wsexpose(wtypes.text, wtypes.text)
    def delete(self, id):
        """Delete this pod.

        :param id: An ID of the pod.
        """
        count = 0
        for pod in self.pod_list:
            if pod.id == id:
                self.pod_list.remove(pod)
                return id
            count = count + 1

        return None
