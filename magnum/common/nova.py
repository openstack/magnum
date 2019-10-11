# Copyright 2019 Catalyst Cloud Ltd.
#
#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

from oslo_config import cfg
from oslo_log import log as logging

from magnum.common import clients
from novaclient import exceptions as nova_exception

LOG = logging.getLogger(__name__)
CONF = cfg.CONF


def get_ssh_key(context, keypair_ident):
    try:
        n_client = clients.OpenStackClients(context).nova()
        keypair = n_client.keypairs.get(keypair_ident)
        # no spaces or break lines at the end, single line string
        return keypair.public_key.strip()
    except nova_exception.NotFound:
        # we don't have a way to tell if the keypair doesn't
        # exist or the cluster is already creted
        return ""
