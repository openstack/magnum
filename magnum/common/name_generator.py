# Copyright 2016 IBM Corp.
# All Rights Reserved.
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

import random


class NameGenerator(object):
    letters = ['alpha', 'beta', 'gamma', 'delta', 'epsilon', 'zeta',
               'eta', 'theta', 'iota', 'kappa', 'lambda', 'mu', 'nu',
               'xi', 'omicron', 'pi', 'rho', 'sigma', 'tau', 'upsilon',
               'phi', 'chi', 'psi', 'omega']

    def __init__(self):
        self.random = random.Random()

    def generate(self):
        """Generate a random name compose of a Greek leter and

        a number, like: beta_2.
        """

        letter = self.random.choice(self.letters)
        number = self.random.randint(1, 24)

        return letter + '-' + str(number)
