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


class Bay(Base):
    id = wtypes.text
    """ The ID of the bays."""

    name = wsme.wsattr(wtypes.text, mandatory=True)
    """ The name of the bay."""

    type = wsme.wsattr(wtypes.text, mandatory=True)
    """ The type of the bay."""

    def __init__(self, **kwargs):
        super(Bay, self).__init__(**kwargs)

    @classmethod
    def sample(cls):
        return cls(id=str(uuid.uuid1()),
                   name='bay_example_A',
                   type='virt')


class BayController(rest.RestController):
    """Manages Bays."""
    def __init__(self, **kwargs):
        super(BayController, self).__init__(**kwargs)

        self.bay_list = []

    @wsme_pecan.wsexpose(Bay, wtypes.text)
    def get_one(self, id):
        """Retrieve details about one bay.

        :param id: An ID of the bay.
        """
        for bay in self.bay_list:
            if bay.id == id:
                return bay
        return None

    @wsme_pecan.wsexpose([Bay], [Query], int)
    def get_all(self, q=None, limit=None):
        """Retrieve definitions of all of the bays.

        :param query: query parameters.
        :param limit: The number of bays to retrieve.
        """
        if len(self.bay_list) == 0:
            return []
        return self.bay_list

    @wsme_pecan.wsexpose(Bay, wtypes.text, wtypes.text)
    def post(self, name, type):
        """Create a new bay.

        :param bay: a bay within the request body.
        """
        bay = Bay(id=str(uuid.uuid1()), name=name, type=type)
        self.bay_list.append(bay)

        return bay

    @wsme_pecan.wsexpose(Bay, wtypes.text, body=Bay)
    def put(self, id, bay):
        """Modify this bay.

        :param id: An ID of the bay.
        :param bay: a bay within the request body.
        """
        pass

    @wsme_pecan.wsexpose(wtypes.text, wtypes.text)
    def delete(self, id):
        """Delete this bay.

        :param id: An ID of the bay.
        """
        count = 0
        for bay in self.bay_list:
            if bay.id == id:
                self.bay_list.remove(bay)
                return id
            count = count + 1

        return None
