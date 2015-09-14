# Copyright 2015 Huawei Technologies Co.,LTD.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from magnum.common.pythonk8sclient.swagger_client import api_client
from magnum.common.pythonk8sclient.swagger_client.apis import apiv_api
from magnum.conductor import utils


class K8sAPI(apiv_api.ApivApi):

    def __init__(self, context, obj):
        # retrieve the URL of the k8s API endpoint
        k8s_api_endpoint = self._retrieve_k8s_api_endpoint(context, obj)

        # build a connection with Kubernetes master
        client = api_client.ApiClient(k8s_api_endpoint)

        super(K8sAPI, self).__init__(client)

    @staticmethod
    def _retrieve_k8s_api_endpoint(context, obj):
        if hasattr(obj, 'bay_uuid'):
            obj = utils.retrieve_bay(context, obj)

        return obj.api_address


def create_k8s_api(context, obj):
    """Create a kubernetes API client

    Creates connection with Kubernetes master and creates ApivApi instance
    to call Kubernetes APIs.

    :param context: The security context
    :param obj: A bay or a k8s object (Pod, Service, ReplicationController)
    """
    return K8sAPI(context, obj)
