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

"""Magnum Docker RPC handler."""

from docker import Client
from docker import tls
from oslo.config import cfg

from magnum.openstack.common import log as logging

LOG = logging.getLogger(__name__)
CONF = cfg.CONF

docker_opts = [
    cfg.StrOpt('host_url',
               help='tcp://host:port to bind/connect to or'
               'unix://path/to/socker to use'),
    cfg.BoolOpt('api_secure',
                default=False,
                help='If set, ignore any SSL validation issues'),
    cfg.StrOpt('ca_file',
               help='Location of CA certificate file for '
               'securing docker api requests (tlscacert).'),
    cfg.StrOpt('cert_file',
               help='Location of TLS certificate file for '
               'securing docker api requests (tlscert).'),
    cfg.StrOpt('key_file',
               help='Location of TLS private key file for '
               'securing docker api requests (tlskey).'),
]

CONF.register_opts(docker_opts, 'docker')

# These are the backend operations.  They are executed by the backend
# service.  API calls via AMQP (within the ReST API) trigger the handlers to
# be called.


class Handler(object):

    def __init__(self, url):
        super(Handler, self).__init__()
        if (CONF.docker.cert_file or
                CONF.docker.key_file):
            client_cert = (CONF.docker.cert_file, CONF.docker.key_file)
        else:
            client_cert = None
        if (CONF.docker.ca_file or
            CONF.docker.api_insecure or
                client_cert):
            tls_config = tls.TLSConfig(
                client_cert=client_cert,
                ca_Cert=CONF.docker.ca_file,
                verify=CONF.docker.api_insecure)
        else:
            tls_config = None
        self.client = Client(base_url=url, tls=tls_config)

    def encode_utf8(self, value):
        return unicode(value).encode('utf-8')

    # Container operations

    def container_create(self, bay_uuid, image_name, command):
        LOG.debug("container_create %s contents=%s" % (bay_uuid, image_name))
        self.client.inspect_image(self._encode_utf8(image_name))
        container_id = self.client.create_container(image_name, command)
        self.container_start(container_id)

    def container_list(self, bay_uuid):
        LOG.debug("container_list")
        container_list = self.client.containers()
        return container_list
        # return container list dict

    def container_delete(self, bay_uuid, container_id):
        LOG.debug("cotainer_delete %s" % bay_uuid)
        return None

    def container_show(self, bay_uuid, container_id):
        LOG.debug("container_show %s" % bay_uuid)
        return None

    def container_reboot(self, bay_uuid, container_id):
        LOG.debug("container_reboot %s" % bay_uuid)
        return None

    def container_stop(self, bay_uuid, container_id):
        LOG.debug("container_stop %s" % bay_uuid)
        self.client.start(container_id)

    def container_start(self, bay_uuid, container_id):
        LOG.debug("container_start %s" % bay_uuid)
        self.client.start(container_id)

    def container_pause(self, bay_uuid, container_id):
        LOG.debug("container_pause %s" % bay_uuid)
        return None

    def container_unpause(self, bay_uuid, container_id):
        LOG.debug("container_unpause %s" % bay_uuid)
        return None

    def container_logs(self, bay_uuid, container_id):
        LOG.debug("container_logs %s" % bay_uuid)
        return None

    def container_execute(self, bay_uuid, container_id):
        LOG.debug("container_execute %s" % bay_uuid)
        return None
