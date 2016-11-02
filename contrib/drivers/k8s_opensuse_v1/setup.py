#!/usr/bin/env python
# Copyright (c) 2016 SUSE Linux GmbH
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import setuptools

setuptools.setup(
    name="k8s_opensuse_v1",
    version="1.0",
    packages=['k8s_opensuse_v1'],
    package_data={
        'k8s_opensuse_v1': ['templates/*', 'templates/fragments/*']
    },
    author="SUSE Linux GmbH",
    author_email="opensuse-cloud@opensuse.org",
    description="Magnum openSUSE Kubernetes driver",
    license="Apache",
    keywords="magnum opensuse driver",
    entry_points={
        'magnum.template_definitions': [
            'k8s_opensuse_v1 = k8s_opensuse_v1:JeOSK8sTemplateDefinition'
        ]
    }
)
