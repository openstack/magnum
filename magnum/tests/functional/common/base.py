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

import logging
import os
import subprocess

from tempest_lib import base

import magnum


class BaseMagnumTest(base.BaseTestCase):
    """Sets up configuration required for functional tests"""

    LOG = logging.getLogger(__name__)

    def __init__(self, *args, **kwargs):
        super(BaseMagnumTest, self).__init__(*args, **kwargs)

    @classmethod
    def copy_logs_handler(cls, get_nodes_fn, coe, keypair):
        """Copy logs closure.

        This method will retrieve all running nodes for a specified bay
        and copy addresses from there locally.

        :param get_nodes_fn: function that takes no parameters and returns
            a list of node IPs to get logs from
        :param coe: the COE type of the nodes
        """
        def int_copy_logs(exec_info):
            try:
                cls.LOG.debug("Copying logs...")
                fn = exec_info[2].tb_frame.f_locals['fn']
                func_name = fn.im_self._get_test_method().__name__
                msg = "Failed to copy logs for bay"
                nodes_addresses = get_nodes_fn()

                for node_address in nodes_addresses:
                    log_name = "node-" + func_name
                    try:
                        base_path = os.path.split(os.path.dirname(
                            os.path.abspath(magnum.__file__)))[0]
                        script = "magnum/tests/contrib/copy_instance_logs.sh"
                        full_location = os.path.join(base_path, script)
                        cls.LOG.debug("running %s" % full_location)
                        cls.LOG.debug("keypair: %s" % keypair)
                        subprocess.check_call([
                            full_location,
                            node_address,
                            coe,
                            log_name,
                            str(keypair)
                        ])
                    except Exception:
                        cls.LOG.exception(msg)
                        cls.LOG.exception("failed to copy from %s to %s%s-%s" %
                                          (node_address,
                                           "/opt/stack/logs/bay-nodes/",
                                           log_name, node_address))
            except Exception:
                cls.LOG.exception(msg)

        return int_copy_logs
