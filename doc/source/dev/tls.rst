..
      Copyright 2015 Rackspace
      All Rights Reserved.

      Licensed under the Apache License, Version 2.0 (the "License"); you may
      not use this file except in compliance with the License. You may obtain
      a copy of the License at

          http://www.apache.org/licenses/LICENSE-2.0

      Unless required by applicable law or agreed to in writing, software
      distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
      WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
      License for the specific language governing permissions and limitations
      under the License.

========================
Transport Layer Security
========================

Magnum uses TLS to secure communication between a Bay's services and the
outside world. This includes not only Magnum itself, but also the end-user
when they choose to use native client libraries to interact with the Bay.
Magnum also uses TLS certificates for client authentication, which means each
client needs a valid certificate to communicate with a Bay.

TLS is a complex subject, and many guides on it exist already. This guide will
not attempt to fully describe TLS, only the necessary pieces to get a client
set up to talk to a Bay with TLS. A more indepth guide on TLS can be found in
the `OpenSSL Cookbook <https://www.feistyduck.com/books/openssl-cookbook/>`_
by Ivan Ristić.


Deploy a secure bay
===================
Magnum supports secure communication between the Magnum service and the
Kubernetes service using TLS. This document explains how to use this feature.

Below is the detailed step for deploying a secure bay and using kubectl to
run Kubernetes commands that uses SSL certificates to communicate with
Kubernetes services running on secure bay.

Create a baymodel, by default TLS is enabled in Magnum::

    magnum baymodel-create --name secure-kubernetes \
                           --keypair-id default \
                           --external-network-id public \
                           --image-id fedora-atomic-latest \
                           --flavor-id m1.small \
                           --docker-volume-size 1 \
                           --coe kubernetes \
                           --network-driver flannel

    +---------------------+--------------------------------------+
    | Property            | Value                                |
    +---------------------+--------------------------------------+
    | http_proxy          | None                                 |
    | updated_at          | None                                 |
    | master_flavor_id    | None                                 |
    | fixed_network       | None                                 |
    | uuid                | 668a5e97-ba92-4b84-bdc3-e2388e0462ea |
    | no_proxy            | None                                 |
    | https_proxy         | None                                 |
    | tls_disabled        | False                                |
    | keypair_id          | default                              |
    | public              | False                                |
    | labels              | {}                                   |
    | docker_volume_size  | 1                                    |
    | external_network_id | public                               |
    | cluster_distro      | fedora-atomic                        |
    | image_id            | fedora-atomic-latest                 |
    | registry_enabled    | False                                |
    | apiserver_port      | None                                 |
    | name                | secure-kubernetes                    |
    | created_at          | 2015-10-08T05:05:10+00:00            |
    | network_driver      | flannel                              |
    | coe                 | kubernetes                           |
    | flavor_id           | m1.small                             |
    | dns_nameserver      | 8.8.8.8                              |
    +---------------------+--------------------------------------+

To disable TLS in magnum use option '--tls-disabled'. Please note it is not
recommended to disable TLS due to security reasons.

Now create a bay. Use the baymodel name as a template for bay creation::

    magnum bay-create --name secure-k8sbay \
                      --baymodel secure-kubernetes \
                      --node-count 1

    +--------------------+------------------------------------------------------------+
    | Property           | Value                                                      |
    +--------------------+------------------------------------------------------------+
    | status             | None                                                       |
    | uuid               | 04952c60-a338-437f-a7e7-d016d1d00e65                       |
    | status_reason      | None                                                       |
    | created_at         | 2015-10-08T04:19:14+00:00                                  |
    | updated_at         | None                                                       |
    | bay_create_timeout | 0                                                          |
    | api_address        | None                                                       |
    | baymodel_id        | da2825a0-6d09-4208-b39e-b2db666f1118                       |
    | node_count         | 1                                                          |
    | node_addresses     | None                                                       |
    | master_count       | 1                                                          |
    | discovery_url      | https://discovery.etcd.io/3b7fb09733429d16679484673ba3bfd5 |
    | name               | secure-k8sbay                                              |
    +--------------------+------------------------------------------------------------+

Now run bay-show command to get the IP of the bay host::

    magnum bay-show secure-k8sbay
    +--------------------+------------------------------------------------------------+
    | Property           | Value                                                      |
    +--------------------+------------------------------------------------------------+
    | status             | CREATE_COMPLETE                                            |
    | uuid               | 04952c60-a338-437f-a7e7-d016d1d00e65                       |
    | status_reason      | Stack CREATE completed successfully                        |
    | created_at         | 2015-10-08T04:19:14+00:00                                  |
    | updated_at         | 2015-10-08T04:21:00+00:00                                  |
    | bay_create_timeout | 0                                                          |
    | api_address        | https://192.168.19.86:6443                                 |
    | baymodel_id        | da2825a0-6d09-4208-b39e-b2db666f1118                       |
    | node_count         | 1                                                          |
    | node_addresses     | [u'192.168.19.88']                                         |
    | master_count       | 1                                                          |
    | discovery_url      | https://discovery.etcd.io/3b7fb09733429d16679484673ba3bfd5 |
    | name               | secure-k8sbay                                              |
    +--------------------+------------------------------------------------------------+

You can see the api_address contains https in URL that denotes the Kubernetes
services are configured securely with SSL certificates and now any
communication to kube-apiserver will be over https making it secure.

Generating a Client Key and Certificate Signing Request
=======================================================

The first step to setting up a client is to generate your personal private key.
This is essentially a cryptographically generated string of bytes. It should be
protected as a password. To generate an RSA key, you will use the 'genrsa'
command of the 'openssl' tool.

::

    openssl genrsa -out client.key 4096

This command generates a 4096 byte RSA key at client.key.

Next, you will need to generate a certificate signing request (CSR). This will
be used by Magnum to generate a signed certificate you will use to communicate
with the Bay. It is used by the Bay to secure the connection and validate you
are you who say you are.

To generate a CSR for client authentication, openssl requires a config file
that specifies a few values. Below is a simple template, just fill in the 'CN'
value with your name and save it as client.conf

::

    $ cat > client.conf << END
    [req]
    distinguished_name = req_distinguished_name
    req_extensions     = req_ext
    prompt = no
    [req_distinguished_name]
    CN = Your Name
    [req_ext]
    extendedKeyUsage = clientAuth
    END

Once you have client.conf, you can run the openssl 'req' command to generate
the CSR.

::

    openssl req -new -days 365 \
        -config client.conf \
        -key client.key \
        -out client.csr


Now that you have your client CSR, you can use the Magnum CLI to send it off
to Magnum to get it signed.

::

    magnum ca-sign secure-k8sbay client.csr > client.crt

The final piece you need to retrieve is the CA certificate for the bay. This
is used by your native client to ensure you're only communicating with hosts
that Magnum set up.

::

    magnum ca-show secure-k8sbay > ca.crt

You need to get kubectl, a kubernetes CLI tool, to communicate with the bay

::

    wget https://github.com/kubernetes/kubernetes/releases/download/v1.0.4/kubernetes.tar.gz
    tar -xzvf kubernetes.tar.gz
    sudo cp -a kubernetes/platforms/linux/amd64/kubectl /usr/bin/kubectl

Now let's run some kubectl commands to check secure communication::

    KUBERNETES_URL=$(magnum bay-show secure-k8sbay |
                     awk '/ api_address /{print $4}')
    kubectl version --certificate-authority=ca.crt \
                    --client-key=client.key \
                    --client-certificate=client.crt -s $KUBERNETES_URL

    Client Version: version.Info{Major:"1", Minor:"0", GitVersion:"v1.0.4", GitCommit:"65d28d5fd12345592405714c81cd03b9c41d41d9", GitTreeState:"clean"}
    Server Version: version.Info{Major:"1", Minor:"0", GitVersion:"v1.0.4", GitCommit:"65d28d5fd12345592405714c81cd03b9c41d41d9", GitTreeState:"clean"}

    kubectl create -f redis-master.yaml --certificate-authority=ca.crt \
                                        --client-key=client.key \
                                        --client-certificate=client.crt -s $KUBERNETES_URL

    pods/test2

    kubectl get pods --certificate-authority=ca.crt \
                     --client-key=client.key \
                     --client-certificate=client.crt -s $KUBERNETES_URL
    NAME           READY     STATUS    RESTARTS   AGE
    redis-master   2/2       Running   0          1m

You can create kubectl configuration for these flags::

    kubectl config set-cluster secure-k8sbay --server=${KUBERNETES_URL} \
        --certificate-authority=${PWD}/ca.crt
    kubectl config set-credentials client --certificate-authority=${PWD}/ca.crt \
        --client-key=${PWD}/client.key --client-certificate=${PWD}/client.crt
    kubectl config set-context secure-k8sbay --cluster=secure-k8sbay --user=client
    kubectl config use-context secure-k8sbay

Now you can use kubectl commands without extra flags::

    kubectl get pods
    NAME           READY     STATUS    RESTARTS   AGE
    redis-master   2/2       Running   0          1m

Access to Kubernetes User Interface::

    curl -L ${KUBERNETES_URL}/ui --cacert ca.crt --key client.key \
        --cert client.crt

    You may also set up kubectl proxy which will use your client certificate to allow you to
    browse to a local address to use the UI without installing a certificate in your browser.

    kubectl proxy --api-prefix=/ --certificate-authority=ca.crt --client-key=client.key \
                  --client-certificate=client.crt -s $KUBERNETES_URL

    Open http://localhost:8001/ui in your browser


Once you have all of these pieces, you can configure your native client. Below
is an example for Docker.

::

    docker -H tcp://192.168.19.86:2376 --tlsverify \
        --tlscacert ca.crt \
        --tlskey client.key \
        --tlscert client.crt \
        info

