# Copyright 2013 - Red Hat, Inc.
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

from wsme import types as wtypes


Uri = wtypes.text


class Link(wtypes.Base):
    """A link representation."""

    href = Uri
    "The link URI."

    target_name = wtypes.text
    "Textual name of the target link."

    @classmethod
    def sample(cls):
        return cls(href=('http://example.com:9777/v1'),
                   target_name='v1')
