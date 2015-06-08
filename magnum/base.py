# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import abc

import six


@six.add_metaclass(abc.ABCMeta)
class BayBase(object):
    pass


@six.add_metaclass(abc.ABCMeta)
class BayFactory(BayBase):
    @abc.abstractmethod
    def list(self):
        pass

    @abc.abstractmethod
    def create(self, pod_definition=None):
        pass

    @abc.abstractmethod
    def get_pod(self, pod_id):
        pass


@six.add_metaclass(abc.ABCMeta)
class Bay(BayBase):
    @abc.abstractmethod
    def destroy(self):
        pass

    @abc.abstractmethod
    def stop(self):
        pass


@six.add_metaclass(abc.ABCMeta)
class ContainerBase(object):
    pass


@six.add_metaclass(abc.ABCMeta)
class PodBase(object):
    pass


@six.add_metaclass(abc.ABCMeta)
class Pod(PodBase):
    pass


@six.add_metaclass(abc.ABCMeta)
class ContainerFactory(ContainerBase):
    @abc.abstractmethod
    def create(self, *args, **kwargs):
        pass

    @abc.abstractmethod
    def list(self):
        pass


@six.add_metaclass(abc.ABCMeta)
class Container(ContainerBase):
    @abc.abstractmethod
    def info(self):
        pass

    @abc.abstractmethod
    def reboot(self):
        pass

    @abc.abstractmethod
    def kill(self):
        pass

    @abc.abstractmethod
    def destroy(self):
        pass

    @abc.abstractmethod
    def logs(self):
        pass

    @abc.abstractmethod
    def pause(self):
        pass

    @abc.abstractmethod
    def unpause(self):
        pass

    @abc.abstractmethod
    def execute(self, cmd):
        pass
