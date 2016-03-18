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

from tempfile import NamedTemporaryFile

from oslo_log import log as logging

from magnum.common.pythonk8sclient.swagger_client import api_client
from magnum.common.pythonk8sclient.swagger_client.apis import apiv_api
from magnum.conductor.handlers.common import cert_manager


LOG = logging.getLogger(__name__)


class K8sAPI(apiv_api.ApivApi):

    def _create_temp_file_with_content(self, content):
        """Creates temp file and write content to the file.

        :param content: file content
        :returns: temp file
        """
        try:
            tmp = NamedTemporaryFile(delete=True)
            tmp.write(content)
            tmp.flush()
        except Exception as err:
            LOG.error("Error while creating temp file: %s", err)
            raise err
        return tmp

    def __init__(self, context, bay):
        self.ca_file = None
        self.cert_file = None
        self.key_file = None

        if bay.magnum_cert_ref:
            self._create_certificate_files(bay)

        # build a connection with Kubernetes master
        client = api_client.ApiClient(bay.api_address,
                                      key_file=self.key_file.name,
                                      cert_file=self.cert_file.name,
                                      ca_certs=self.ca_file.name)

        super(K8sAPI, self).__init__(client)

    def _create_certificate_files(self, bay):
        """Read certificate and key for a bay and stores in files.

        :param bay: Bay object
        """
        magnum_cert_obj = cert_manager.get_bay_magnum_cert(bay)
        self.cert_file = self._create_temp_file_with_content(
            magnum_cert_obj.get_certificate())
        private_key = magnum_cert_obj.get_decrypted_private_key()
        self.key_file = self._create_temp_file_with_content(
            private_key)
        ca_cert_obj = cert_manager.get_bay_ca_certificate(bay)
        self.ca_file = self._create_temp_file_with_content(
            ca_cert_obj.get_certificate())

    def __del__(self):
        if self.ca_file:
            self.ca_file.close()
        if self.cert_file:
            self.cert_file.close()
        if self.key_file:
            self.key_file.close()


def create_k8s_api(context, bay):
    """Create a kubernetes API client

    Creates connection with Kubernetes master and creates ApivApi instance
    to call Kubernetes APIs.

    :param context: The security context
    :param bay:  Bay object
    """
    return K8sAPI(context, bay)
