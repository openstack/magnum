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

import tempfile

from kubernetes import client as k8s_config
from kubernetes.client import api_client
from kubernetes.client.apis import core_v1_api
from kubernetes.client import configuration as k8s_configuration
from kubernetes.client import rest
from oslo_log import log as logging

from magnum.conductor.handlers.common.cert_manager import create_client_files

LOG = logging.getLogger(__name__)


class ApiClient(api_client.ApiClient):

    def __init__(self, configuration=None, header_name=None,
                 header_value=None, cookie=None):
        if configuration is None:
            configuration = k8s_configuration.Configuration()
        self.configuration = configuration

        self.rest_client = rest.RESTClientObject(configuration)
        self.default_headers = {}
        if header_name is not None:
            self.default_headers[header_name] = header_value
        self.cookie = cookie

    def __del__(self):
        pass

    def call_api(self, resource_path, method,
                 path_params=None, query_params=None, header_params=None,
                 body=None, post_params=None, files=None,
                 response_type=None, auth_settings=None,
                 _return_http_data_only=None, collection_formats=None,
                 _preload_content=True, _request_timeout=None, **kwargs):
        """Makes http request (synchronous) and return the deserialized data

        :param resource_path: Path to method endpoint.
        :param method: Method to call.
        :param path_params: Path parameters in the url.
        :param query_params: Query parameters in the url.
        :param header_params: Header parameters to be
            placed in the request header.
        :param body: Request body.
        :param post_params dict: Request post form parameters,
            for `application/x-www-form-urlencoded`, `multipart/form-data`.
        :param auth_settings list: Auth Settings names for the request.
        :param response: Response data type.
        :param files dict: key -> filename, value -> filepath,
            for `multipart/form-data`.
        :param _return_http_data_only: response data without head status code
                                       and headers
        :param collection_formats: dict of collection formats for path, query,
            header, and post parameters.
        :param _preload_content: if False, the urllib3.HTTPResponse object will
                                 be returned without reading/decoding response
                                 data. Default is True.
        :param _request_timeout: timeout setting for this request. If one
                                 number provided, it will be total request
                                 timeout. It can also be a pair (tuple) of
                                 (connection, read) timeouts.

        :return: The method will return the response directly

        """
        return self.__call_api(resource_path, method,
                               path_params, query_params, header_params,
                               body, post_params, files,
                               response_type, auth_settings,
                               _return_http_data_only, collection_formats,
                               _preload_content, _request_timeout)


class K8sAPI(core_v1_api.CoreV1Api):

    def _create_temp_file_with_content(self, content):
        """Creates temp file and write content to the file.

        :param content: file content
        :returns: temp file
        """
        try:
            tmp = tempfile.NamedTemporaryFile(delete=True)
            tmp.write(content)
            tmp.flush()
        except Exception as err:
            LOG.error("Error while creating temp file: %s", err)
            raise
        return tmp

    def __init__(self, context, cluster):
        self.ca_file = None
        self.cert_file = None
        self.key_file = None

        if cluster.magnum_cert_ref:
            (self.ca_file, self.key_file,
             self.cert_file) = create_client_files(cluster, context)

        config = k8s_config.Configuration()
        config.host = cluster.api_address
        config.ssl_ca_cert = self.ca_file.name
        config.cert_file = self.cert_file.name
        config.key_file = self.key_file.name

        # build a connection with Kubernetes master
        client = ApiClient(configuration=config)

        super(K8sAPI, self).__init__(client)

    def __del__(self):
        if self.ca_file:
            self.ca_file.close()
        if self.cert_file:
            self.cert_file.close()
        if self.key_file:
            self.key_file.close()


def create_k8s_api(context, cluster):
    """Create a kubernetes API client

    Creates connection with Kubernetes master and creates ApivApi instance
    to call Kubernetes APIs.

    :param context: The security context
    :param cluster:  Cluster object
    """
    return K8sAPI(context, cluster)
