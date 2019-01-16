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


class ClusterTemplatePatchData(models.BaseModel):
    """Data that encapsulates  clustertemplatepatch attributes"""
    pass


class ClusterTemplatePatchEntity(models.EntityModel):
    """Model that represents a single instance of ClusterTemplatePatchData"""
    ENTITY_NAME = 'clustertemplatepatch'
    MODEL_TYPE = ClusterTemplatePatchData


class ClusterTemplatePatchCollection(models.CollectionModel):
    """Model that represents a list of ClusterTemplatePatchData objects"""
    MODEL_TYPE = ClusterTemplatePatchData
    COLLECTION_NAME = 'clustertemplatepatchlist'

    def to_json(self):
        """Converts ClusterTemplatePatchCollection to json

        Retrieves list from COLLECTION_NAME attribute and converts each object
        to dict, appending it to a list.  Then converts the entire list to
        json

        This is required due to COLLECTION_NAME holding a list of objects that
        needed to be converted to dict individually

        :returns: json object
        """

        data = getattr(self, ClusterTemplatePatchCollection.COLLECTION_NAME)
        collection = []
        for d in data:
            collection.append(d.to_dict())
        return jsonutils.dumps(collection)

    @classmethod
    def from_dict(cls, data):
        """Converts dict to ClusterTemplatePatchData

        Converts data dict to list of ClusterTemplatePatchData objects and
        stores it in COLLECTION_NAME

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
