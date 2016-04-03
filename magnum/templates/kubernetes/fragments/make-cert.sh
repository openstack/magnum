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

set -o errexit
set -o nounset
set -o pipefail

. /etc/sysconfig/heat-params

if [ "$TLS_DISABLED" == "True" ]; then
  exit 0
fi

cert_ip=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)
sans="IP:${cert_ip},IP:${KUBE_API_PUBLIC_ADDRESS},IP:${KUBE_API_PRIVATE_ADDRESS},IP:127.0.0.1"
MASTER_HOSTNAME=${MASTER_HOSTNAME:-}
if [[ -n "${MASTER_HOSTNAME}" ]]; then
  sans="${sans},DNS:${MASTER_HOSTNAME}"
fi

cert_dir=/srv/kubernetes
cert_conf_dir=${cert_dir}/conf
cert_group=root

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
USER_TOKEN=`curl -s -i -X POST -H "Content-Type: application/json" -d "$auth_json" \
                 $AUTH_URL/auth/tokens | grep X-Subject-Token | awk '{print $2}'`

# Get CA certificate for this bay
curl -X GET \
  -H "X-Auth-Token: $USER_TOKEN" \
  $MAGNUM_URL/certificates/$BAY_UUID | python -c 'import sys, json; print json.load(sys.stdin)["pem"]' > ${CA_CERT}

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
csr_req=$(python -c "import json; fp = open('${SERVER_CSR}'); print json.dumps({'bay_uuid': '$BAY_UUID', 'csr': fp.read()}); fp.close()")
curl -X POST \
    -H "X-Auth-Token: $USER_TOKEN" \
    -H "Content-Type: application/json" \
    -d "$csr_req" \
    $MAGNUM_URL/certificates | python -c 'import sys, json; print json.load(sys.stdin)["pem"]' > ${SERVER_CERT}

chmod 500 "${cert_dir}"
chown -R kube:kube "${cert_dir}"
