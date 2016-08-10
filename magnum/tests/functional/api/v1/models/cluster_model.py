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

from magnum.tests.functional.common import models


class ClusterData(models.BaseModel):
    """Data that encapsulates cluster attributes"""
    pass


class ClusterEntity(models.EntityModel):
    """Entity Model that represents a single instance of ClusterData"""
    ENTITY_NAME = 'cluster'
    MODEL_TYPE = ClusterData


class ClusterCollection(models.CollectionModel):
    """Collection Model that represents a list of ClusterData objects"""
    COLLECTION_NAME = 'clusterlists'
    MODEL_TYPE = ClusterData
