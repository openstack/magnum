# Copyright 2015 Huawei Technologies Co.,LTD.
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

import decorator
from oslo_config import cfg
import pecan

from magnum.common import exception
from magnum import objects


def enforce_bay_types(*bay_types):
    @decorator.decorator
    def wrapper(func, *args, **kwargs):
        obj = args[1]
        bay = objects.Bay.get_by_uuid(pecan.request.context, obj.bay_uuid)
        baymodel = objects.BayModel.get_by_uuid(pecan.request.context,
                                                bay.baymodel_id)
        if baymodel.coe not in bay_types:
            raise exception.InvalidParameterValue(
                'Cannot fulfill request with a %(bay_type)s bay, '
                'expecting a %(supported_bay_types)s bay.' %
                {'bay_type': baymodel.coe,
                 'supported_bay_types': '/'.join(bay_types)})

        return func(*args, **kwargs)

    return wrapper


def enforce_network_driver_types_create():
    @decorator.decorator
    def wrapper(func, *args, **kwargs):
        baymodel = args[1]
        _enforce_network_driver_types(baymodel)
        return func(*args, **kwargs)

    return wrapper


def enforce_network_driver_types_update():
    @decorator.decorator
    def wrapper(func, *args, **kwargs):
        uuid = args[1]
        baymodel = objects.BayModel.get_by_uuid(pecan.request.context, uuid)
        _enforce_network_driver_types(baymodel)
        return func(*args, **kwargs)

    return wrapper


def _enforce_network_driver_types(baymodel):
    driver = baymodel.network_driver
    if driver:
        validator = Validator.get_coe_validator(baymodel.coe)
        validator.validate_network_driver(driver)


class Validator(object):

    @staticmethod
    def get_coe_validator(coe):
        if coe == 'kubernetes':
            return K8sValidator()
        if coe == 'swarm':
            return SwarmValidator()
        if coe == 'mesos':
            return MesosValidator()
        raise exception.InvalidParameterValue(
            'Requested COE type %s is not supported.' % coe)

    @classmethod
    def validate_network_driver(cls, driver):
        cls._validate_network_driver_supported(driver)
        cls._validate_network_driver_allowed(driver)

    @classmethod
    def _validate_network_driver_supported(cls, driver):
        """Confirm that driver is supported by Magnum for this COE."""
        if driver not in cls.supported_drivers:
            raise exception.InvalidParameterValue(
                'Network driver type %(driver)s is not supported, '
                'expecting a %(supported_drivers)s network driver.' % {
                    'driver': driver,
                    'supported_drivers': '/'.join(
                        cls.supported_drivers + ['unspecified'])})

    @classmethod
    def _validate_network_driver_allowed(cls, driver):
        """Confirm that driver is allowed via configuration for this COE."""
        allowed_drivers = cfg.CONF.baymodel[cls.allowed_driver_config]
        if ('all' not in allowed_drivers and
           driver not in allowed_drivers):
            raise exception.InvalidParameterValue(
                'Network driver type %(driver)s is not allowed, '
                'expecting a %(allowed_drivers)s network driver. '
                'Check %(config)s configuration.' % {
                    'driver': driver,
                    'allowed_drivers': '/'.join(
                        allowed_drivers + ['unspecified']),
                    'config': cls.allowed_driver_config})


class K8sValidator(Validator):

    supported_drivers = ['flannel']
    allowed_driver_config = 'kubernetes_allowed_network_drivers'


class SwarmValidator(Validator):

    supported_drivers = ['docker']
    allowed_driver_config = 'swarm_allowed_network_drivers'


class MesosValidator(Validator):

    supported_drivers = ['docker']
    allowed_driver_config = 'mesos_allowed_network_drivers'
