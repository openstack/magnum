# Copyright (c) 2018 NEC, Corp.
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

import sys

from oslo_upgradecheck import common_checks
from oslo_upgradecheck import upgradecheck

import magnum.conf
from magnum.i18n import _

CONF = magnum.conf.CONF


class Checks(upgradecheck.UpgradeCommands):

    """Contains upgrade checks

    Various upgrade checks should be added as separate methods in this class
    and added to _upgrade_checks tuple.
    """

    _upgrade_checks = (
        (_('Policy File JSON to YAML Migration'),
         (common_checks.check_policy_json, {'conf': CONF})),
    )


def main():
    return upgradecheck.main(
        CONF, project='magnum', upgrade_command=Checks())


if __name__ == '__main__':
    sys.exit(main())
