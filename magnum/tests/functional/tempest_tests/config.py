# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from __future__ import print_function

from oslo_config import cfg
from tempest import config  # noqa


service_available_group = cfg.OptGroup(name="service_available",
                                       title="Available OpenStack Services")

ServiceAvailableGroup = [
    cfg.BoolOpt("magnum",
                default=True,
                help="Whether or not magnum is expected to be available"),
]

magnum_group = cfg.OptGroup(name="magnum", title="Magnum Options")

MagnumGroup = [
    cfg.StrOpt("image_id",
               default="fedora-atomic-latest",
               help="Image id to be used for baymodel."),

    cfg.StrOpt("nic_id",
               default="public",
               help="NIC id."),

    cfg.StrOpt("keypair_id",
               default="default",
               help="Keypair id to use to log into nova instances."),

    cfg.StrOpt("flavor_id",
               default="s1.magnum",
               help="Flavor id to use for baymodels."),

    cfg.StrOpt("magnum_url",
               default=None,
               help="Bypass URL for Magnum to skip service catalog lookup"),

    cfg.StrOpt("master_flavor_id",
               default="m1.magnum",
               help="Master flavor id to use for baymodels."),

    cfg.StrOpt("csr_location",
               default="/opt/stack/new/magnum/default.csr",
               help="CSR location for certificates."),

    cfg.StrOpt("dns_nameserver",
               default="8.8.8.8",
               help="DNS nameserver to use for baymodels."),

    cfg.StrOpt("copy_logs",
               default=True,
               help="Specify whether to copy nova server logs on failure."),
]
