# Copyright 2015 Rackspace US, Inc.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from oslo_config import cfg
from stevedore import driver

CONF = cfg.CONF

DEFAULT_CERT_MANAGER = 'barbican'

cert_manager_opts = [
    cfg.StrOpt('cert_manager_type',
               default=DEFAULT_CERT_MANAGER,
               help='Certificate Manager plugin. '
                    'Defaults to {0}.'.format(DEFAULT_CERT_MANAGER))
]

CONF.register_opts(cert_manager_opts, group='certificates')

_CERT_MANAGER_PLUGIN = None


def get_backend():
    global _CERT_MANAGER_PLUGIN
    if not _CERT_MANAGER_PLUGIN:
        _CERT_MANAGER_PLUGIN = driver.DriverManager(
            "magnum.cert_manager.backend",
            cfg.CONF.certificates.cert_manager_type).driver
    return _CERT_MANAGER_PLUGIN
