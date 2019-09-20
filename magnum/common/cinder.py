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
from magnum.common import exception

LOG = logging.getLogger(__name__)
CONF = cfg.CONF


def get_default_docker_volume_type(context):
    return (CONF.cinder.default_docker_volume_type or
            _get_random_volume_type(context))


def get_default_boot_volume_type(context):
    return (CONF.cinder.default_boot_volume_type or
            _get_random_volume_type(context))


def get_default_etcd_volume_type(context):
    return (CONF.cinder.default_etcd_volume_type or
            _get_random_volume_type(context))


def _get_random_volume_type(context):
    c_client = clients.OpenStackClients(context).cinder()
    volume_types = c_client.volume_types.list()
    if volume_types:
        return volume_types[0].name
    else:
        raise exception.VolumeTypeNotFound()
