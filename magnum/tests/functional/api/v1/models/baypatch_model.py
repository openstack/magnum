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

from oslo_serialization import jsonutils

from magnum.tests.functional.common import models


class BayPatchData(models.BaseModel):
    """Data that encapsulates  baypatch attributes"""
    pass


class BayPatchEntity(models.EntityModel):
    """Entity Model that represents a single instance of BayPatchData"""
    ENTITY_NAME = 'baypatch'
    MODEL_TYPE = BayPatchData


class BayPatchCollection(models.CollectionModel):
    """Collection Model that represents a list of BayPatchData objects"""
    MODEL_TYPE = BayPatchData
    COLLECTION_NAME = 'baypatchlist'

    def to_json(self):
        """Converts BayPatchCollection to json

        Retrieves list from COLLECTION_NAME attribute and converts each object
        to dict, appending it to a list.  Then converts the entire list to json

        This is required due to COLLECTION_NAME holding a list of objects that
        needed to be converted to dict individually

        :returns: json object
        """

        data = getattr(self, BayPatchCollection.COLLECTION_NAME)
        collection = []
        for d in data:
            collection.append(d.to_dict())
        return jsonutils.dumps(collection)

    @classmethod
    def from_dict(cls, data):
        """Converts dict to BayPatchData

        Converts data dict to list of BayPatchData objects and stores it
        in COLLECTION_NAME

        Example of dict data:

            [{
                "path": "/name",
                "value": "myname",
                "op": "replace"
            }]

        :param data: dict of patch data
        :returns: json object
        """

        model = cls()
        collection = []
        for d in data:
            collection.append(cls.MODEL_TYPE.from_dict(d))
        setattr(model, cls.COLLECTION_NAME, collection)
        return model
