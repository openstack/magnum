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

import yaml

import certifi

from magnum.common import clients
from magnum.common import utils
import magnum.conf

CONF = magnum.conf.CONF


def get_openstack_ca_certificate():
    # This function returns the CA bundle to use when verifying TLS
    # connections to the OpenStack API in both the Cluster API provider
    # and OpenStack integrations on the cluster (e.g. OCCM, Cinder CSI)
    #
    # If no CA bundle is specified in config we use the CA bundle from
    # certifi
    # This is because the Cluster API provider contains NO trusted CAs
    # and, because it is a pod in Kubernetes, it does NOT pick up the
    # trusted CAs from the host
    ca_certificate = utils.get_openstack_ca()
    if not ca_certificate:
        with open(certifi.where(), "r") as ca_file:
            ca_certificate = ca_file.read()
    return ca_certificate


def _create_app_cred(context, cluster):
    osc = clients.OpenStackClients(context)
    appcred = osc.keystone().client.application_credentials.create(
        user=cluster.user_id,
        name=f"magnum-{cluster.uuid}",
        description=f"Magnum cluster ({cluster.uuid})",
    )
    return {
        "clouds": {
            "openstack": {
                "identity_api_version": 3,
                "region_name": osc.cinder_region_name(),
                "interface": CONF.nova_client.endpoint_type.replace("URL", ""),
                # This config item indicates whether TLS should be
                # verified when connecting to the OpenStack API
                "verify": CONF.drivers.verify_ca,
                "auth": {
                    "auth_url": osc.url_for(
                        service_type="identity", interface="public"
                    ),
                    "application_credential_id": appcred.id,
                    "application_credential_secret": appcred.secret,
                },
            },
        },
    }


def get_app_cred_yaml(context, cluster):
    app_cred_dict = _create_app_cred(context, cluster)
    return yaml.safe_dump(app_cred_dict)
