#!/usr/bin/python

# Copyright 2015 Rackspace, Inc.
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

import json
import os
import subprocess
import sys

import requests


HEAT_PARAMS_PATH = '/etc/sysconfig/heat-params'
PUBLIC_IP_URL = 'http://169.254.169.254/latest/meta-data/public-ipv4'
CERT_DIR = '/etc/docker'
CERT_CONF_DIR = '%s/conf' % CERT_DIR
CA_CERT_PATH = '%s/ca.crt' % CERT_DIR
SERVER_CONF_PATH = '%s/server.conf' % CERT_CONF_DIR
SERVER_KEY_PATH = '%s/server.key' % CERT_DIR
SERVER_CSR_PATH = '%s/server.csr' % CERT_DIR
SERVER_CERT_PATH = '%s/server.crt' % CERT_DIR

CSR_CONFIG_TEMPLATE = """
[req]
distinguished_name = req_distinguished_name
req_extensions     = req_ext
x509_extensions    = req_ext
prompt = no
copy_extensions = copyall
[req_distinguished_name]
CN = swarm.invalid
[req_ext]
subjectAltName = %(subject_alt_names)s
extendedKeyUsage = clientAuth,serverAuth
"""


def _parse_config_value(value):
    parsed_value = value
    if parsed_value[-1] == '\n':
        parsed_value = parsed_value[:-1]
    return parsed_value[1:-1]


def load_config():
    config = dict()
    with open(HEAT_PARAMS_PATH, 'r') as fp:
        for line in fp.readlines():
            key, value = line.split('=', 1)
            config[key] = _parse_config_value(value)
    return config


def create_dirs():
    os.makedirs(CERT_CONF_DIR)


def _get_public_ip():
    return requests.get(PUBLIC_IP_URL, timeout=60).text


def _build_subject_alt_names(config):
    ips = {
        config['SWARM_NODE_IP'],
        config['SWARM_API_IP'],
        '127.0.0.1',
    }
    # NOTE(mgoddard): If floating IP is disabled, these can be empty.
    public_ip = _get_public_ip()
    if public_ip:
        ips.add(public_ip)
    api_ip = config['API_IP_ADDRESS']
    if api_ip:
        ips.add(api_ip)
    subject_alt_names = ['IP:%s' % ip for ip in ips]
    return ','.join(subject_alt_names)


def write_ca_cert(config, verify_ca):
    cluster_cert_url = '%s/certificates/%s' % (config['MAGNUM_URL'],
                                               config['CLUSTER_UUID'])
    headers = {'X-Auth-Token': config['USER_TOKEN'],
               'OpenStack-API-Version': 'container-infra latest'}
    ca_cert_resp = requests.get(cluster_cert_url,
                                headers=headers,
                                verify=verify_ca, timeout=60)

    with open(CA_CERT_PATH, 'w') as fp:
        fp.write(ca_cert_resp.json()['pem'])


def write_server_key():
    subprocess.check_call(
        ['openssl', 'genrsa',
         '-out', SERVER_KEY_PATH,
         '4096'])


def _write_csr_config(config):
    with open(SERVER_CONF_PATH, 'w') as fp:
        params = {
            'subject_alt_names': _build_subject_alt_names(config)
        }
        fp.write(CSR_CONFIG_TEMPLATE % params)


def create_server_csr(config):
    _write_csr_config(config)
    subprocess.check_call(
        ['openssl', 'req', '-new',
         '-days', '1000',
         '-key', SERVER_KEY_PATH,
         '-out', SERVER_CSR_PATH,
         '-reqexts', 'req_ext',
         '-extensions', 'req_ext',
         '-config', SERVER_CONF_PATH])

    with open(SERVER_CSR_PATH, 'r') as fp:
        return {'cluster_uuid': config['CLUSTER_UUID'], 'csr': fp.read()}


def write_server_cert(config, csr_req, verify_ca):
    cert_url = '%s/certificates' % config['MAGNUM_URL']
    headers = {
        'Content-Type': 'application/json',
        'X-Auth-Token': config['USER_TOKEN'],
        'OpenStack-API-Version': 'container-infra latest'
    }
    csr_resp = requests.post(cert_url,
                             data=json.dumps(csr_req),
                             headers=headers,
                             verify=verify_ca, timeout=60)

    with open(SERVER_CERT_PATH, 'w') as fp:
        fp.write(csr_resp.json()['pem'])


def get_user_token(config, verify_ca):
    creds_str = '''
{
    "auth": {
        "identity": {
            "methods": [
                "password"
            ],
            "password": {
                "user": {
                    "id": "%(trustee_user_id)s",
                    "password": "%(trustee_password)s"
                }
            }
        }
    }
}
'''
    params = {
        'trustee_user_id': config['TRUSTEE_USER_ID'],
        'trustee_password': config['TRUSTEE_PASSWORD'],
    }
    creds = creds_str % params
    headers = {'Content-Type': 'application/json'}
    url = config['AUTH_URL'] + '/auth/tokens'
    r = requests.post(url, headers=headers, data=creds, verify=verify_ca,
                      timeout=60)
    config['USER_TOKEN'] = r.headers['X-Subject-Token']
    return config


def main():
    config = load_config()
    if config['TLS_DISABLED'] == 'False':
        verify_ca = True if config['VERIFY_CA'] == 'True' else False
        create_dirs()
        config = get_user_token(config, verify_ca)
        write_ca_cert(config, verify_ca)
        write_server_key()
        csr_req = create_server_csr(config)
        write_server_cert(config, csr_req, verify_ca)


if __name__ == '__main__':
    sys.exit(main())
