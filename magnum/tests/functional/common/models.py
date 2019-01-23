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


class BaseModel(object):
    """Superclass Responsible for converting json data to/from model"""

    @classmethod
    def from_json(cls, json_str):
        return cls.from_dict(jsonutils.loads(json_str))

    def to_json(self):
        return jsonutils.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, data):
        model = cls()
        for key in data:
            setattr(model, key, data.get(key))
        return model

    def to_dict(self):
        result = {}
        for key in self.__dict__:
            result[key] = getattr(self, key)
            if isinstance(result[key], BaseModel):
                result[key] = result[key].to_dict()
        return result

    def __str__(self):
        return "%s" % self.to_dict()


class EntityModel(BaseModel):
    """Superclass responsible from converting dict to instance of model"""

    @classmethod
    def from_dict(cls, data):
        model = super(EntityModel, cls).from_dict(data)
        if hasattr(model, cls.ENTITY_NAME):
            val = getattr(model, cls.ENTITY_NAME)
            setattr(model, cls.ENTITY_NAME, cls.MODEL_TYPE.from_dict(val))
        return model


class CollectionModel(BaseModel):
    """Superclass responsible from converting dict to list of models"""

    @classmethod
    def from_dict(cls, data):
        model = super(CollectionModel, cls).from_dict(data)

        collection = []
        if hasattr(model, cls.COLLECTION_NAME):
            for d in getattr(model, cls.COLLECTION_NAME):
                collection.append(cls.MODEL_TYPE.from_dict(d))
            setattr(model, cls.COLLECTION_NAME, collection)

        return model
