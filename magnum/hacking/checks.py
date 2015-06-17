# Copyright (c) 2015 Intel, Inc.
# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import re

"""
Guidelines for writing new hacking checks

 - Use only for Magnum specific tests. OpenStack general tests
   should be submitted to the common 'hacking' module.
 - Pick numbers in the range M3xx. Find the current test with
   the highest allocated number and then pick the next value.
   If nova has an N3xx code for that test, use the same number.
 - Keep the test method code in the source file ordered based
   on the M3xx value.
 - List the new rule in the top level HACKING.rst file
 - Add test cases for each new rule to magnum/tests/unit/test_hacking.py

"""

enforce_re = re.compile(r"@policy.enforce_wsgi*")
decorator_re = re.compile(r"@.*")


def check_policy_enforce_decorator(logical_line,
                                   previous_logical, blank_before,
                                   filename):
    msg = ("M301: the policy.enforce_wsgi decorator must be the "
           "first decorator on a method.")
    if (blank_before == 0 and re.match(enforce_re, logical_line)
            and re.match(decorator_re, previous_logical)):
        yield(0, msg)


def factory(register):
    register(check_policy_enforce_decorator)
