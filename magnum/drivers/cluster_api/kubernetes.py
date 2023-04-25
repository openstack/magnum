# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import base64
import copy
import os
import pathlib
import re
import tempfile
import yaml

from oslo_log import log as logging
import requests

from magnum import conf


LOG = logging.getLogger(__name__)
CONF = conf.CONF


def file_or_data(obj, file_key):
    """Returns a path to a file containing the requested data.

    First check if there is a file path already,
    if the data is there, put it in a file,
    and return a path to the temp directory
    """
    if file_key in obj:
        return obj[file_key]

    data_key = file_key + "-data"
    if data_key in obj:
        # TODO(johngarbutt) check permissions on this file!
        # and check how it gets deleted
        with tempfile.NamedTemporaryFile(delete=False) as fd:
            fd.write(base64.standard_b64decode(obj[data_key]))
        return fd.name

    return None


class Client(requests.Session):
    """Object for producing Kubernetes clients."""

    KUBECONFIG_ENV_NAME = "KUBECONFIG"

    def __init__(self, kubeconfig):
        super().__init__()
        cluster, user = self._get_cluster_and_user(kubeconfig)

        self.server = cluster["server"].rstrip("/")
        ca_file = file_or_data(cluster, "certificate-authority")
        if ca_file:
            self.verify = ca_file

        # convert certs into files as required by requests
        client_cert = file_or_data(user, "client-certificate")
        assert client_cert is not None
        self.cert = (client_cert, file_or_data(user, "client-key"))

    def _get_cluster_and_user(self, kubeconfig):
        # get the context
        current_context = kubeconfig["current-context"]
        context = [
            c["context"]
            for c in kubeconfig["contexts"]
            if c["name"] == current_context
        ][0]
        # extract cluster and user from context
        cluster = [
            c["cluster"]
            for c in kubeconfig["clusters"]
            if c["name"] == context["cluster"]
        ][0]
        user = [
            u["user"]
            for u in kubeconfig["users"]
            if u["name"] == context["user"]
        ][0]
        return cluster, user

    @classmethod
    def _get_kubeconfig_path(cls):
        # use config if specified
        if CONF.capi_driver.kubeconfig_file:
            return CONF.capi_driver.kubeconfig_file
        if cls.KUBECONFIG_ENV_NAME in os.environ:
            return os.environ[cls.KUBECONFIG_ENV_NAME]
        # the default kubeconfig location
        return pathlib.Path.home() / ".kube" / "config"

    @classmethod
    def _load_kubeconfig(cls, path):
        with open(path) as fd:
            return yaml.safe_load(fd)

    @classmethod
    def load(cls):
        path = cls._get_kubeconfig_path()
        kubeconfig = cls._load_kubeconfig(path)
        return Client(kubeconfig)

    def request(self, method, url, *args, **kwargs):
        # Make sure to add the server to any relative URLs
        if re.match(r"^http(s)://", url) is None:
            url = "{}{}".format(self.server, url)
        response = super().request(method, url, *args, **kwargs)
        LOG.debug(
            'Kubernetes API request: "%s %s" %s',
            method,
            url,
            response.status_code,
        )
        return response

    def ensure_namespace(self, namespace):
        Namespace(self).apply(namespace)

    def apply_secret(self, secret_name, data, namespace):
        Secret(self).apply(secret_name, data, namespace)


class Resource:
    def __init__(self, client):
        self.client = client
        assert hasattr(self, "api_version")
        self.kind = getattr(self, "kind", type(self).__name__)
        self.plural_name = getattr(
            self, "plural_name", self.kind.lower() + "s"
        )
        self.namespaced = getattr(self, "namespaced", True)

    def prepare_path(self, name=None, namespace=None):
        # Begin with either /api or /apis depending whether the api version
        # is the core API
        prefix = "/apis" if "/" in self.api_version else "/api"
        # Include the namespace unless the resource is namespaced
        path_namespace = f"/namespaces/{namespace}" if namespace else ""
        # Include the resource name if given
        path_name = f"/{name}" if name else ""
        return (
            f"{prefix}/{self.api_version}{path_namespace}/"
            f"{self.plural_name}{path_name}"
        )

    def apply(self, name, data=None, namespace=None):
        """Applies the given object to the target Kubernetes cluster."""
        assert self.namespaced == bool(namespace)
        body_data = copy.deepcopy(data) if data else {}
        body_data["apiVersion"] = self.api_version
        body_data["kind"] = self.kind
        body_data.setdefault("metadata", {})["name"] = name
        if namespace:
            body_data["metadata"]["namespace"] = namespace
        response = self.client.patch(
            self.prepare_path(name, namespace),
            json=body_data,
            headers={"Content-Type": "application/apply-patch+yaml"},
            params={"fieldManager": "magnum", "force": "true"},
        )
        response.raise_for_status()
        return response.json()


class Namespace(Resource):
    api_version = "v1"
    namespaced = False


class Secret(Resource):
    api_version = "v1"
