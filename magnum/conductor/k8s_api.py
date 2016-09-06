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

from k8sclient.client import api_client
from k8sclient.client.apis import apiv_api
from oslo_log import log as logging

from magnum.conductor.handlers.common.cert_manager import create_client_files
from magnum.i18n import _LE

LOG = logging.getLogger(__name__)


class K8sAPI(apiv_api.ApivApi):

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
            LOG.error(_LE("Error while creating temp file: %s"), err)
            raise
        return tmp

    def __init__(self, context, cluster):
        self.ca_file = None
        self.cert_file = None
        self.key_file = None

        if cluster.magnum_cert_ref:
            (self.ca_file, self.key_file,
             self.cert_file) = create_client_files(cluster, context)

        # build a connection with Kubernetes master
        client = api_client.ApiClient(cluster.api_address,
                                      key_file=self.key_file.name,
                                      cert_file=self.cert_file.name,
                                      ca_certs=self.ca_file.name)

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
