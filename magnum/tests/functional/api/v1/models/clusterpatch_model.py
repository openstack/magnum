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


class ClusterPatchData(models.BaseModel):
    """Data that encapsulates  clusterpatch attributes"""
    pass


class ClusterPatchEntity(models.EntityModel):
    """Entity Model that represents a single instance of ClusterPatchData"""
    ENTITY_NAME = 'clusterpatch'
    MODEL_TYPE = ClusterPatchData


class ClusterPatchCollection(models.CollectionModel):
    """Collection Model that represents a list of ClusterPatchData objects"""
    MODEL_TYPE = ClusterPatchData
    COLLECTION_NAME = 'clusterpatchlist'

    def to_json(self):
        """Converts ClusterPatchCollection to json

        Retrieves list from COLLECTION_NAME attribute and converts each object
        to dict, appending it to a list.  Then converts the entire list to json

        This is required due to COLLECTION_NAME holding a list of objects that
        needed to be converted to dict individually

        :returns: json object
        """

        data = getattr(self, ClusterPatchCollection.COLLECTION_NAME)
        collection = []
        for d in data:
            collection.append(d.to_dict())
        return jsonutils.dumps(collection)

    @classmethod
    def from_dict(cls, data):
        """Converts dict to ClusterPatchData

        Converts data dict to list of ClusterPatchData objects and stores it
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
