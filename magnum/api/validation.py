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

from magnum.api import utils as api_utils
from magnum.common import exception
from magnum.common import utils
from magnum.i18n import _
from magnum import objects


baymodel_opts = [
    cfg.ListOpt('kubernetes_allowed_network_drivers',
                default=['all'],
                help=_("Allowed network drivers for kubernetes baymodels. "
                       "Use 'all' keyword to allow all drivers supported "
                       "for kubernetes baymodels. Supported network drivers "
                       "include flannel.")),
    cfg.StrOpt('kubernetes_default_network_driver',
               default='flannel',
               help=_("Default network driver for kubernetes baymodels.")),
    cfg.ListOpt('swarm_allowed_network_drivers',
                default=['all'],
                help=_("Allowed network drivers for docker swarm baymodels. "
                       "Use 'all' keyword to allow all drivers supported "
                       "for swarm baymodels. Supported network drivers "
                       "include docker and flannel.")),
    cfg.StrOpt('swarm_default_network_driver',
               default='docker',
               help=_("Default network driver for docker swarm baymodels.")),
    cfg.ListOpt('mesos_allowed_network_drivers',
                default=['all'],
                help=_("Allowed network drivers for mesos baymodels. "
                       "Use 'all' keyword to allow all drivers supported "
                       "for mesos baymodels. Supported network drivers "
                       "include docker.")),
    cfg.StrOpt('mesos_default_network_driver',
               default='docker',
               help=_("Default network driver for mesos baymodels.")),
]
cfg.CONF.register_opts(baymodel_opts, group='baymodel')


def enforce_bay_types(*bay_types):
    """Enforce that bay_type is in supported list."""
    @decorator.decorator
    def wrapper(func, *args, **kwargs):
        # Note(eliqiao): This decorator has some assumptions
        # args[1] should be an APIBase instance or
        # args[2] should be a bay_ident
        obj = args[1]
        if hasattr(obj, 'bay_uuid'):
            bay = objects.Bay.get_by_uuid(pecan.request.context, obj.bay_uuid)
        else:
            bay_ident = args[2]
            if utils.is_uuid_like(bay_ident):
                bay = objects.Bay.get_by_uuid(pecan.request.context, bay_ident)
            else:
                bay = objects.Bay.get_by_name(pecan.request.context, bay_ident)

        if bay.baymodel.coe not in bay_types:
            raise exception.InvalidParameterValue(_(
                'Cannot fulfill request with a %(bay_type)s bay, '
                'expecting a %(supported_bay_types)s bay.') %
                {'bay_type': bay.baymodel.coe,
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
        baymodel_ident = args[1]
        baymodel = api_utils.get_rpc_resource('BayModel', baymodel_ident)
        _enforce_network_driver_types(baymodel)
        return func(*args, **kwargs)

    return wrapper


def _enforce_network_driver_types(baymodel):
    validator = Validator.get_coe_validator(baymodel.coe)
    if not baymodel.network_driver:
        baymodel.network_driver = validator.default_driver
    validator.validate_network_driver(baymodel.network_driver)


class Validator(object):

    validators = {}

    @classmethod
    def get_coe_validator(cls, coe):
        if not cls.validators:
            cls.validators = {
                'kubernetes': K8sValidator(),
                'swarm': SwarmValidator(),
                'mesos': MesosValidator(),
            }
        if coe in cls.validators:
            return cls.validators[coe]
        else:
            raise exception.InvalidParameterValue(
                _('Requested COE type %s is not supported.') % coe)

    @classmethod
    def validate_network_driver(cls, driver):
        cls._validate_network_driver_supported(driver)
        cls._validate_network_driver_allowed(driver)

    @classmethod
    def _validate_network_driver_supported(cls, driver):
        """Confirm that driver is supported by Magnum for this COE."""
        if driver not in cls.supported_drivers:
            raise exception.InvalidParameterValue(_(
                'Network driver type %(driver)s is not supported, '
                'expecting a %(supported_drivers)s network driver.') % {
                    'driver': driver,
                    'supported_drivers': '/'.join(
                        cls.supported_drivers + ['unspecified'])})

    @classmethod
    def _validate_network_driver_allowed(cls, driver):
        """Confirm that driver is allowed via configuration for this COE."""
        if ('all' not in cls.allowed_drivers and
           driver not in cls.allowed_drivers):
            raise exception.InvalidParameterValue(_(
                'Network driver type %(driver)s is not allowed, '
                'expecting a %(allowed_drivers)s network driver. ') % {
                    'driver': driver,
                    'allowed_drivers': '/'.join(
                        cls.allowed_drivers + ['unspecified'])})


class K8sValidator(Validator):

    supported_drivers = ['flannel']
    allowed_drivers = cfg.CONF.baymodel.kubernetes_allowed_network_drivers
    default_driver = cfg.CONF.baymodel.kubernetes_default_network_driver


class SwarmValidator(Validator):

    supported_drivers = ['docker', 'flannel']
    allowed_drivers = cfg.CONF.baymodel.swarm_allowed_network_drivers
    default_driver = cfg.CONF.baymodel.swarm_default_network_driver


class MesosValidator(Validator):

    supported_drivers = ['docker']
    allowed_drivers = cfg.CONF.baymodel.mesos_allowed_network_drivers
    default_driver = cfg.CONF.baymodel.mesos_default_network_driver
