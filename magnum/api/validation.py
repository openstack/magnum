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
from oslo_utils import uuidutils
import pecan

from magnum.api import utils as api_utils
from magnum.common import exception
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


bay_update_allowed_properties = set(['node_count'])


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
            if uuidutils.is_uuid_like(bay_ident):
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
        patch = args[2]
        baymodel = api_utils.get_resource('BayModel', baymodel_ident)
        try:
            baymodel_dict = api_utils.apply_jsonpatch(baymodel.as_dict(),
                                                      patch)
        except api_utils.JSONPATCH_EXCEPTIONS as e:
            raise exception.PatchError(patch=patch, reason=e)
        baymodel = objects.BayModel(pecan.request.context, **baymodel_dict)
        _enforce_network_driver_types(baymodel)
        return func(*args, **kwargs)

    return wrapper


def _enforce_network_driver_types(baymodel):
    validator = Validator.get_coe_validator(baymodel.coe)
    if not baymodel.network_driver:
        baymodel.network_driver = validator.default_network_driver
    validator.validate_network_driver(baymodel.network_driver)


def enforce_volume_driver_types_create():
    @decorator.decorator
    def wrapper(func, *args, **kwargs):
        baymodel = args[1]
        _enforce_volume_driver_types(baymodel.as_dict())
        return func(*args, **kwargs)

    return wrapper


def enforce_volume_driver_types_update():
    @decorator.decorator
    def wrapper(func, *args, **kwargs):
        baymodel_ident = args[1]
        patch = args[2]
        baymodel = api_utils.get_resource('BayModel', baymodel_ident)
        try:
            baymodel_dict = api_utils.apply_jsonpatch(baymodel.as_dict(),
                                                      patch)
        except api_utils.JSONPATCH_EXCEPTIONS as e:
            raise exception.PatchError(patch=patch, reason=e)
        _enforce_volume_driver_types(baymodel_dict)
        return func(*args, **kwargs)

    return wrapper


def _enforce_volume_driver_types(baymodel):
    validator = Validator.get_coe_validator(baymodel['coe'])
    if not baymodel.get('volume_driver'):
        return
    validator.validate_volume_driver(baymodel['volume_driver'])


def validate_bay_properties(delta):

    update_disallowed_properties = delta - bay_update_allowed_properties
    if update_disallowed_properties:
        err = (_("cannot change bay property(ies) %s.") %
               ", ".join(update_disallowed_properties))
        raise exception.InvalidParameterValue(err=err)


class Validator(object):

    @classmethod
    def get_coe_validator(cls, coe):
        if coe == 'kubernetes':
            return K8sValidator()
        elif coe == 'swarm':
            return SwarmValidator()
        elif coe == 'mesos':
            return MesosValidator()
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
        if driver not in cls.supported_network_drivers:
            raise exception.InvalidParameterValue(_(
                'Network driver type %(driver)s is not supported, '
                'expecting a %(supported_drivers)s network driver.') % {
                    'driver': driver,
                    'supported_drivers': '/'.join(
                        cls.supported_network_drivers + ['unspecified'])})

    @classmethod
    def _validate_network_driver_allowed(cls, driver):
        """Confirm that driver is allowed via configuration for this COE."""
        if ('all' not in cls.allowed_network_drivers and
           driver not in cls.allowed_network_drivers):
            raise exception.InvalidParameterValue(_(
                'Network driver type %(driver)s is not allowed, '
                'expecting a %(allowed_drivers)s network driver. ') % {
                    'driver': driver,
                    'allowed_drivers': '/'.join(
                        cls.allowed_network_drivers + ['unspecified'])})

    @classmethod
    def validate_volume_driver(cls, driver):
        cls._validate_volume_driver_supported(driver)

    @classmethod
    def _validate_volume_driver_supported(cls, driver):
        """Confirm that volume driver is supported by Magnum for this COE."""
        if driver not in cls.supported_volume_driver:
            raise exception.InvalidParameterValue(_(
                'Volume driver type %(driver)s is not supported, '
                'expecting a %(supported_volume_driver)s volume driver.') % {
                    'driver': driver,
                    'supported_volume_driver': '/'.join(
                        cls.supported_volume_driver + ['unspecified'])})


class K8sValidator(Validator):

    supported_network_drivers = ['flannel']
    allowed_network_drivers = (
        cfg.CONF.baymodel.kubernetes_allowed_network_drivers)
    default_network_driver = (
        cfg.CONF.baymodel.kubernetes_default_network_driver)

    supported_volume_driver = ['cinder']


class SwarmValidator(Validator):

    supported_network_drivers = ['docker', 'flannel']
    allowed_network_drivers = cfg.CONF.baymodel.swarm_allowed_network_drivers
    default_network_driver = cfg.CONF.baymodel.swarm_default_network_driver

    supported_volume_driver = ['rexray']


class MesosValidator(Validator):

    supported_network_drivers = ['docker']
    allowed_network_drivers = cfg.CONF.baymodel.mesos_allowed_network_drivers
    default_network_driver = cfg.CONF.baymodel.mesos_default_network_driver

    supported_volume_driver = ['rexray']
