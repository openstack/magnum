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

cert_dir=/srv/kubernetes
cert_conf_dir=${cert_dir}/conf

mkdir -p "$cert_dir"
mkdir -p "$cert_conf_dir"

CA_CERT=$cert_dir/ca.crt
CLIENT_CERT=$cert_dir/client.crt
CLIENT_CSR=$cert_dir/client.csr
CLIENT_KEY=$cert_dir/client.key

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
    $MAGNUM_URL/certificates/$CLUSTER_UUID | python -c 'import sys, json; print json.load(sys.stdin)["pem"]' > $CA_CERT

# Create config for client's csr
cat > ${cert_conf_dir}/client.conf <<EOF
[req]
distinguished_name = req_distinguished_name
req_extensions     = req_ext
prompt = no
[req_distinguished_name]
CN = kubernetes.invalid
[req_ext]
keyUsage=critical,digitalSignature,keyEncipherment
extendedKeyUsage=clientAuth
subjectAltName=dirName:kubelet,dirName:kubeproxy
[kubelet]
CN=kubelet
[kubeproxy]
CN=kube-proxy
EOF

# Generate client's private key and csr
openssl genrsa -out "${CLIENT_KEY}" 4096
chmod 400 "${CLIENT_KEY}"
openssl req -new -days 1000 \
        -key "${CLIENT_KEY}" \
        -out "${CLIENT_CSR}" \
        -reqexts req_ext \
        -config "${cert_conf_dir}/client.conf"

# Send csr to Magnum to have it signed
csr_req=$(python -c "import json; fp = open('${CLIENT_CSR}'); print json.dumps({'cluster_uuid': '$CLUSTER_UUID', 'csr': fp.read()}); fp.close()")
curl -k -X POST \
    -H "X-Auth-Token: $USER_TOKEN" \
    -H "Content-Type: application/json" \
    -d "$csr_req" \
    $MAGNUM_URL/certificates | python -c 'import sys, json; print json.load(sys.stdin)["pem"]' > ${CLIENT_CERT}

# Common certs and key are created for both etcd and kubernetes services.
# Both etcd and kube user should have permission to access the certs and key.
groupadd kube_etcd
usermod -a -G kube_etcd etcd
usermod -a -G kube_etcd kube
chmod 550 "${cert_dir}"
chown -R kube:kube_etcd "${cert_dir}"
chmod 440 $CLIENT_KEY

sed -i '
    s|CA_CERT|'"$CA_CERT"'|
    s|CLIENT_CERT|'"$CLIENT_CERT"'|
    s|CLIENT_KEY|'"$CLIENT_KEY"'|
' /srv/kubernetes/kubeconfig.yaml
