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


class Container(Base):
    """Container Model."""

    id = wtypes.text
    """ The ID of the containers."""

    name = wsme.wsattr(wtypes.text, mandatory=True)
    """ The name of the container."""

    desc = wsme.wsattr(wtypes.text, mandatory=True)

    def __init__(self, **kwargs):
        super(Container, self).__init__(**kwargs)

    def as_dict(self):
        return self.as_dict_from_keys(['id', 'name', 'desc'])

    @classmethod
    def sample(cls):
        return cls(id=str(uuid.uuid1()),
                   name="Docker",
                   desc='Docker Containers')


class StartController(object):
    @wsme_pecan.wsexpose(wtypes.text, wtypes.text)
    def _default(self, id):
        return "Start Container %s" % id


class StopController(object):
    @wsme_pecan.wsexpose(wtypes.text, wtypes.text)
    def _default(self, id, *remainder):
        return "Stop Container %s" % id


class RebootController(object):
    @wsme_pecan.wsexpose(wtypes.text, wtypes.text)
    def _default(self, id, *remainder):
        return "Reboot Container %s" % id


class PauseController(object):
    @wsme_pecan.wsexpose(wtypes.text, wtypes.text)
    def _default(self, id, *remainder):
        return "Pause Container %s" % id


class UnpauseController(object):
    @wsme_pecan.wsexpose(wtypes.text, wtypes.text)
    def _default(self, id, *remainder):
        return "Unpause Container %s" % id


class LogsController(object):
    @wsme_pecan.wsexpose(wtypes.text, wtypes.text)
    def _default(self, id, *remainder):
        return "Logs Container %s" % id


class ExecuteController(object):
    @wsme_pecan.wsexpose(wtypes.text, wtypes.text)
    def _default(self, id, *remainder):
        return "Execute Container %s" % id


class ContainerController(rest.RestController):
    """Manages Containers."""

    start = StartController()
    stop = StopController()
    reboot = RebootController()
    pause = PauseController()
    unpause = UnpauseController()
    logs = LogsController()
    execute = ExecuteController()

    def __init__(self, **kwargs):
        super(ContainerController, self).__init__(**kwargs)

        self.container_list = []

    @wsme_pecan.wsexpose(Container, wtypes.text)
    def get_one(self, id):
        """Retrieve details about one container.

        :param id: An ID of the container.
        """
        for container in self.container_list:
            if container.id == id:
                return container
        return None

    @wsme_pecan.wsexpose([Container], [Query], int)
    def get_all(self, q=None, limit=None):
        """Retrieve definitions of all of the containers.

        :param query: query parameters.
        :param limit: The number of containers to retrieve.
        """
        if len(self.container_list) == 0:
            return []
        return self.container_list

    @wsme_pecan.wsexpose(Container, body=Container)
    def post(self, container):
        """Create a new container.

        :param container: a container within the request body.
        """
        container.id = str(uuid.uuid1())
        self.container_list.append(container)

        return container

    @wsme_pecan.wsexpose(Container, wtypes.text, body=Container)
    def put(self, id, container):
        """Modify this container.

        :param id: An ID of the container.
        :param container: a container within the request body.
        """
        pass

    @wsme_pecan.wsexpose(wtypes.text, wtypes.text)
    def delete(self, id):
        """Delete this container.

        :param id: An ID of the container.
        """
        count = 0
        for container in self.container_list:
            if container.id == id:
                self.container_list.remove(container)
                return id
            count += 1

        return None
