#!/bin/sh

# Copyright 2014 The Kubernetes Authors All rights reserved.
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

. /etc/sysconfig/heat-params

set -o errexit
set -o nounset
set -o pipefail

if [ "$TLS_DISABLED" == "True" ]; then
    exit 0
fi

if [[ -z "${KUBE_NODE_PUBLIC_IP}" ]]; then
    KUBE_NODE_PUBLIC_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)
fi
if [[ -z "${KUBE_NODE_IP}" ]]; then
    KUBE_NODE_IP=$(curl -s http://169.254.169.254/latest/meta-data/local-ipv4)
fi

sans="IP:${KUBE_NODE_PUBLIC_IP},IP:${KUBE_NODE_IP}"
if [ "${KUBE_NODE_PUBLIC_IP}" != "${KUBE_API_PUBLIC_ADDRESS}" ] \
        && [ -n "${KUBE_API_PUBLIC_ADDRESS}" ]; then
    sans="${sans},IP:${KUBE_API_PUBLIC_ADDRESS}"
fi
if [ "${KUBE_NODE_IP}" != "${KUBE_API_PRIVATE_ADDRESS}" ] \
        && [ -n "${KUBE_API_PRIVATE_ADDRESS}" ]; then
    sans="${sans},IP:${KUBE_API_PRIVATE_ADDRESS}"
fi
MASTER_HOSTNAME=${MASTER_HOSTNAME:-}
if [[ -n "${MASTER_HOSTNAME}" ]]; then
    sans="${sans},DNS:${MASTER_HOSTNAME}"
fi
sans="${sans},IP:127.0.0.1"

cert_dir=/srv/kubernetes
cert_conf_dir=${cert_dir}/conf

mkdir -p "$cert_dir"
mkdir -p "$cert_conf_dir"

CA_CERT=$cert_dir/ca.crt
SERVER_CERT=$cert_dir/server.crt
SERVER_CSR=$cert_dir/server.csr
SERVER_KEY=$cert_dir/server.key

#Get a token by user credentials and trust
auth_json=$(cat << EOF
{
    "auth": {
        "identity": {
            "methods": [
                "password"
            ],
            "password": {
                "user": {
                    "id": "$TRUSTEE_USER_ID",
                    "password": "$TRUSTEE_PASSWORD"
                }
            }
        },
        "scope": {
            "OS-TRUST:trust": {
                "id": "$TRUST_ID"
            }
        }
    }
}
EOF
)

#trust is introduced in Keystone v3 version
AUTH_URL=${AUTH_URL/v2.0/v3}
content_type='Content-Type: application/json'
url="$AUTH_URL/auth/tokens"
USER_TOKEN=`curl -k -s -i -X POST -H "$content_type" -d "$auth_json" $url \
    | grep X-Subject-Token | awk '{print $2}' | tr -d '[[:space:]]'`

# Get CA certificate for this cluster
curl -k -X GET \
    -H "X-Auth-Token: $USER_TOKEN" \
    $MAGNUM_URL/certificates/$CLUSTER_UUID | python -c 'import sys, json; print json.load(sys.stdin)["pem"]' > ${CA_CERT}

# Create config for server's csr
cat > ${cert_conf_dir}/server.conf <<EOF
[req]
distinguished_name = req_distinguished_name
req_extensions     = req_ext
prompt = no
[req_distinguished_name]
CN = kubernetes.invalid
[req_ext]
subjectAltName = ${sans}
extendedKeyUsage = clientAuth,serverAuth
EOF

# Generate server's private key and csr
openssl genrsa -out "${SERVER_KEY}" 4096
chmod 400 "${SERVER_KEY}"
openssl req -new -days 1000 \
        -key "${SERVER_KEY}" \
        -out "${SERVER_CSR}" \
        -reqexts req_ext \
        -config "${cert_conf_dir}/server.conf"

# Send csr to Magnum to have it signed
csr_req=$(python -c "import json; fp = open('${SERVER_CSR}'); print json.dumps({'cluster_uuid': '$CLUSTER_UUID', 'csr': fp.read()}); fp.close()")
curl -k -X POST \
    -H "X-Auth-Token: $USER_TOKEN" \
    -H "Content-Type: application/json" \
    -d "$csr_req" \
    $MAGNUM_URL/certificates | python -c 'import sys, json; print json.load(sys.stdin)["pem"]' > ${SERVER_CERT}

# Common certs and key are created for both etcd and kubernetes services.
# Both etcd and kube user should have permission to access the certs and key.
groupadd kube_etcd
usermod -a -G kube_etcd etcd
usermod -a -G kube_etcd kube
chmod 550 "${cert_dir}"
chown -R kube:kube_etcd "${cert_dir}"
chmod 440 $SERVER_KEY
