#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import base64
import os
import pathlib
import tempfile
from unittest import mock
import yaml

import requests

from magnum.drivers.cluster_api import kubernetes
from magnum.tests import base

TEST_SERVER = "https://test:6443"
TEST_KUBECONFIG_YAML = f"""\
apiVersion: v1
clusters:
- cluster:
    certificate-authority: "cafile"
    server: {TEST_SERVER}
  name: default
contexts:
- context:
    cluster: default
    user: default
  name: default
current-context: default
kind: Config
users:
- name: default
  user:
    client-certificate: "certfile"
    client-key: "keyfile"
"""
TEST_KUBECONFIG = yaml.safe_load(TEST_KUBECONFIG_YAML)


class TestKubernetesClient(base.TestCase):
    def test_file_or_data(self):
        data = kubernetes.file_or_data(dict(key="mydata"), "key")
        self.assertEqual("mydata", data)

    @mock.patch.object(tempfile, "NamedTemporaryFile")
    def test_file_or_data_create_temp(self, mock_temp):
        data = kubernetes.file_or_data(
            {"key-data": base64.b64encode(b"mydata").decode("utf-8")}, "key"
        )
        mock_temp.assert_has_calls(
            [
                mock.call(delete=False),
                mock.call().__enter__(),
                mock.call().__enter__().write(b"mydata"),
                mock.call().__exit__(None, None, None),
            ]
        )
        self.assertEqual(mock_temp().__enter__().name, data)

    def test_file_or_data_missing(self):
        data = kubernetes.file_or_data(dict(), "key")
        self.assertIsNone(data)

    def test_client_constructor(self):
        client = kubernetes.Client(TEST_KUBECONFIG)

        self.assertEqual(TEST_SERVER, client.server)
        self.assertEqual("cafile", client.verify)
        self.assertEqual(("certfile", "keyfile"), client.cert)

    def test_get_kubeconfig_path_default(self):
        self.assertEqual(
            pathlib.Path.home() / ".kube" / "config",
            kubernetes.Client._get_kubeconfig_path(),
        )

    def test_get_kubeconfig_path_config(self):
        os.environ["KUBECONFIG"] = "bar"
        self.config(kubeconfig_file="foo", group="capi_driver")

        path = kubernetes.Client._get_kubeconfig_path()

        del os.environ["KUBECONFIG"]
        self.assertEqual("foo", path)

    def test_get_kubeconfig_path_env(self):
        os.environ["KUBECONFIG"] = "bar"

        path = kubernetes.Client._get_kubeconfig_path()

        del os.environ["KUBECONFIG"]
        self.assertEqual("bar", path)

    @mock.patch(
        "builtins.open",
        new_callable=mock.mock_open,
        read_data=TEST_KUBECONFIG_YAML,
    )
    def test_client_load(self, mock_open):
        self.config(kubeconfig_file="mypath", group="capi_driver")

        client = kubernetes.Client.load()

        self.assertEqual(TEST_SERVER, client.server)
        mock_open.assert_called_once_with("mypath")

    @mock.patch.object(requests.Session, "request")
    def test_ensure_namespace(self, mock_request):
        client = kubernetes.Client(TEST_KUBECONFIG)

        client.ensure_namespace("namespace1")

        mock_request.assert_called_once_with(
            "PATCH",
            "https://test:6443/api/v1/namespaces/namespace1",
            data=None,
            json={
                "apiVersion": "v1",
                "kind": "Namespace",
                "metadata": {"name": "namespace1"},
            },
            headers={"Content-Type": "application/apply-patch+yaml"},
            params={"fieldManager": "magnum", "force": "true"},
        )

    @mock.patch.object(requests.Session, "request")
    def test_apply_secret(self, mock_request):
        client = kubernetes.Client(TEST_KUBECONFIG)
        test_data = dict(
            stringData=dict(foo="bar"), metadata=dict(labels=dict(baz="asdf"))
        )

        client.apply_secret("secname", test_data, "ns1")

        mock_request.assert_called_once_with(
            "PATCH",
            "https://test:6443/api/v1/namespaces/ns1/secrets/secname",
            data=None,
            json={
                "stringData": {"foo": "bar"},
                "apiVersion": "v1",
                "kind": "Secret",
                "metadata": {
                    "labels": {"baz": "asdf"},
                    "name": "secname",
                    "namespace": "ns1",
                },
            },
            headers={"Content-Type": "application/apply-patch+yaml"},
            params={"fieldManager": "magnum", "force": "true"},
        )

    @mock.patch.object(requests.Session, "request")
    def test_delete_all_secrets_by_label(self, mock_request):
        client = kubernetes.Client(TEST_KUBECONFIG)
        mock_response = mock.MagicMock()
        mock_request.return_value = mock_response

        client.delete_all_secrets_by_label("label", "cluster1", "ns1")

        mock_request.assert_called_once_with(
            "DELETE",
            "https://test:6443/api/v1/namespaces/ns1/secrets",
            params={"labelSelector": "label=cluster1"},
        )
        mock_response.raise_for_status.assert_called_once_with()

    @mock.patch.object(requests.Session, "request")
    def test_get_capi_cluster_found(self, mock_request):
        client = kubernetes.Client(TEST_KUBECONFIG)
        mock_response = mock.MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = "mock_json"
        mock_request.return_value = mock_response

        cluster = client.get_capi_cluster("name", "ns1")

        mock_request.assert_called_once_with(
            "GET",
            (
                "https://test:6443/apis/cluster.x-k8s.io/"
                "v1beta1/namespaces/ns1/clusters/name"
            ),
            allow_redirects=True,
        )
        self.assertEqual("mock_json", cluster)

    @mock.patch.object(requests.Session, "request")
    def test_get_capi_cluster_not_found(self, mock_request):
        client = kubernetes.Client(TEST_KUBECONFIG)
        mock_response = mock.MagicMock()
        mock_response.status_code = 404
        mock_request.return_value = mock_response

        cluster = client.get_capi_cluster("name", "ns1")

        self.assertIsNone(cluster)

    @mock.patch.object(requests.Session, "request")
    def test_get_capi_cluster_error(self, mock_request):
        client = kubernetes.Client(TEST_KUBECONFIG)
        mock_response = mock.MagicMock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = requests.HTTPError
        mock_request.return_value = mock_response

        self.assertRaises(
            requests.HTTPError, client.get_capi_cluster, "name", "ns1"
        )

    @mock.patch.object(requests.Session, "request")
    def test_get_kubeadm_control_plane_found(self, mock_request):
        client = kubernetes.Client(TEST_KUBECONFIG)
        mock_response = mock.MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = "mock_json"
        mock_request.return_value = mock_response

        cluster = client.get_kubeadm_control_plane("name", "ns1")

        mock_request.assert_called_once_with(
            "GET",
            (
                "https://test:6443/apis/controlplane.cluster.x-k8s.io/"
                "v1beta1/namespaces/ns1/kubeadmcontrolplanes/name"
            ),
            allow_redirects=True,
        )
        self.assertEqual("mock_json", cluster)

    @mock.patch.object(requests.Session, "request")
    def test_get_machine_deployment_found(self, mock_request):
        client = kubernetes.Client(TEST_KUBECONFIG)
        mock_response = mock.MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = "mock_json"
        mock_request.return_value = mock_response

        cluster = client.get_machine_deployment("name", "ns1")

        mock_request.assert_called_once_with(
            "GET",
            (
                "https://test:6443/apis/cluster.x-k8s.io/"
                "v1beta1/namespaces/ns1/machinedeployments/name"
            ),
            allow_redirects=True,
        )
        self.assertEqual("mock_json", cluster)

    @mock.patch.object(requests.Session, "request")
    def test_get_manifests_by_label_found(self, mock_request):
        items = [
            {
                "kind": "Manifests",
                "metadata": {
                    "name": f"manifests{idx}",
                    "namespace": "ns1"
                },
            }
            for idx in range(5)
        ]

        mock_response = mock.Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "metadata": {
                "continue": "",
            },
            "items": items,
        }
        mock_request.return_value = mock_response

        client = kubernetes.Client(TEST_KUBECONFIG)
        manifests = client.get_manifests_by_label("label", "cluster1", "ns1")

        mock_request.assert_called_once_with(
            "GET",
            (
                "https://test:6443/apis/addons.stackhpc.com/"
                "v1alpha1/namespaces/ns1/manifests"
            ),
            params={"labelSelector": "label=cluster1"},
            allow_redirects=True
        )
        self.assertEqual(items, manifests)

    @mock.patch.object(requests.Session, "request")
    def test_get_helm_releases_by_label_found(self, mock_request):
        items = [
            {
                "kind": "HelmRelease",
                "metadata": {
                    "name": f"helmrelease{idx}",
                    "namespace": "ns1"
                },
            }
            for idx in range(5)
        ]

        mock_response = mock.Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "metadata": {
                "continue": "",
            },
            "items": items,
        }
        mock_request.return_value = mock_response

        client = kubernetes.Client(TEST_KUBECONFIG)
        helm_releases = client.get_helm_releases_by_label(
            "label",
            "cluster1",
            "ns1"
        )

        mock_request.assert_called_once_with(
            "GET",
            (
                "https://test:6443/apis/addons.stackhpc.com/"
                "v1alpha1/namespaces/ns1/helmreleases"
            ),
            params={"labelSelector": "label=cluster1"},
            allow_redirects=True
        )
        self.assertEqual(items, helm_releases)

    @mock.patch.object(requests.Session, "request")
    def test_get_helm_releases_by_label_multipage(self, mock_request):
        items = [
            {
                "kind": "HelmRelease",
                "metadata": {
                    "name": f"helmrelease{idx}",
                    "namespace": "ns1"
                },
            }
            for idx in range(10)
        ]

        mock_response_page1 = mock.Mock()
        mock_response_page1.raise_for_status.return_value = None
        mock_response_page1.json.return_value = {
            "metadata": {
                "continue": "continuetoken",
            },
            "items": items[:5],
        }
        mock_response_page2 = mock.Mock()
        mock_response_page2.raise_for_status.return_value = None
        mock_response_page2.json.return_value = {
            "metadata": {
                "continue": "",
            },
            "items": items[5:],
        }
        mock_request.side_effect = [
            mock_response_page1,
            mock_response_page2,
        ]

        client = kubernetes.Client(TEST_KUBECONFIG)
        helm_releases = client.get_helm_releases_by_label(
            "label",
            "cluster1",
            "ns1"
        )

        self.assertEqual(mock_request.call_count, 2)
        mock_request.assert_has_calls([
            mock.call(
                "GET",
                (
                    "https://test:6443/apis/addons.stackhpc.com/"
                    "v1alpha1/namespaces/ns1/helmreleases"
                ),
                params={"labelSelector": "label=cluster1"},
                allow_redirects=True
            ),
            mock.call(
                "GET",
                (
                    "https://test:6443/apis/addons.stackhpc.com/"
                    "v1alpha1/namespaces/ns1/helmreleases"
                ),
                params={
                    "labelSelector": "label=cluster1",
                    "continue": "continuetoken",
                },
                allow_redirects=True
            ),
        ])
        self.assertEqual(items, helm_releases)

    @mock.patch.object(kubernetes.Client, "get_helm_releases_by_label")
    @mock.patch.object(kubernetes.Client, "get_manifests_by_label")
    def test_get_addons_by_label_found(
        self,
        mock_get_manifests,
        mock_get_helm_releases
    ):
        manifests = [
            {
                "kind": "Manifests",
                "metadata": {
                    "name": f"manifests{idx}",
                    "namespace": "ns1"
                },
            }
            for idx in range(5)
        ]
        helm_releases = [
            {
                "kind": "HelmRelease",
                "metadata": {
                    "name": f"helmrelease{idx}",
                    "namespace": "ns1"
                },
            }
            for idx in range(5)
        ]

        mock_get_manifests.return_value = manifests
        mock_get_helm_releases.return_value = helm_releases

        client = kubernetes.Client(TEST_KUBECONFIG)
        addons = client.get_addons_by_label("label", "cluster1", "ns1")

        mock_get_manifests.assert_called_once_with(
            "label",
            "cluster1",
            "ns1"
        )
        mock_get_helm_releases.assert_called_once_with(
            "label",
            "cluster1",
            "ns1"
        )
        self.assertEqual(manifests + helm_releases, addons)
