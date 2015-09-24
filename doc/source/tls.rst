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

    [req]
    distinguished_name = req_distinguished_name
    req_extensions     = req_ext
    x509_extensions    = req_ext
    prompt = no
    [req_distinguished_name]
    CN = Your Name
    [req_ext]
    extendedKeyUsage = clientAuth

Once you have client.conf, you can run the openssl 'req' command to generate
the CSR.

::

    openssl req -new -days 365
        -config client.conf
        -reqexts req_ext
        -extensions req_ext
        -key client.key
        -out client.csr


Now that you have your client CSR, you can use the Magnum CLI to send it off
to Magnum to get it signed.

::

    magnum ca-sign --bay <bay-id> --csr client.csr > client.crt

The final piece you need to retrieve is the CA certificate for the bay. This
is used by your native client to ensure you're only communicating with hosts
that Magnum set up.

::

    magnum ca-show --bay <bay-id> > ca.crt

Once you have all of these pieces, you can configure your native client. Below
is an example for Docker.

::

    docker -H tcp://<bay_api_address>:2376 --tls --tlsverify \
        --tlscacert ca.crt \
        --tlskey client.key \
        --tlscert client.crt
        info
