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

from stevedore import driver

import magnum.conf

CONF = magnum.conf.CONF

_CERT_MANAGER_PLUGIN = None


def get_backend():
    global _CERT_MANAGER_PLUGIN
    if not _CERT_MANAGER_PLUGIN:
        _CERT_MANAGER_PLUGIN = driver.DriverManager(
            "magnum.cert_manager.backend",
            CONF.certificates.cert_manager_type).driver
    return _CERT_MANAGER_PLUGIN
