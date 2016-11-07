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

from oslo_utils import uuidutils
import pecan

from magnum.api import utils as api_utils
from magnum.common import exception
import magnum.conf
from magnum.i18n import _
from magnum import objects

CONF = magnum.conf.CONF

cluster_update_allowed_properties = set(['node_count'])


def enforce_cluster_types(*cluster_types):
    """Enforce that cluster_type is in supported list."""
    @decorator.decorator
    def wrapper(func, *args, **kwargs):
        # Note(eliqiao): This decorator has some assumptions
        # args[1] should be an APIBase instance or
        # args[2] should be a cluster_ident
        obj = args[1]
        if hasattr(obj, 'cluster_uuid'):
            cluster = objects.Cluster.get_by_uuid(pecan.request.context,
                                                  obj.cluster_uuid)
        else:
            cluster_ident = args[2]
            if uuidutils.is_uuid_like(cluster_ident):
                cluster = objects.Cluster.get_by_uuid(pecan.request.context,
                                                      cluster_ident)
            else:
                cluster = objects.Cluster.get_by_name(pecan.request.context,
                                                      cluster_ident)

        if cluster.cluster_template.coe not in cluster_types:
            raise exception.InvalidParameterValue(_(
                'Cannot fulfill request with a %(cluster_type)s cluster, '
                'expecting a %(supported_cluster_types)s cluster.') %
                {'cluster_type': cluster.cluster_template.coe,
                 'supported_cluster_types': '/'.join(cluster_types)})

        return func(*args, **kwargs)

    return wrapper


def enforce_network_driver_types_create():
    @decorator.decorator
    def wrapper(func, *args, **kwargs):
        cluster_template = args[1]
        _enforce_network_driver_types(cluster_template)
        return func(*args, **kwargs)

    return wrapper


def enforce_network_driver_types_update():
    @decorator.decorator
    def wrapper(func, *args, **kwargs):
        cluster_template_ident = args[1]
        patch = args[2]
        cluster_template = api_utils.get_resource('ClusterTemplate',
                                                  cluster_template_ident)
        try:
            cluster_template_dict = api_utils.apply_jsonpatch(
                cluster_template.as_dict(), patch)
        except api_utils.JSONPATCH_EXCEPTIONS as e:
            raise exception.PatchError(patch=patch, reason=e)
        cluster_template = objects.ClusterTemplate(pecan.request.context,
                                                   **cluster_template_dict)
        _enforce_network_driver_types(cluster_template)
        return func(*args, **kwargs)

    return wrapper


def _enforce_network_driver_types(cluster_template):
    validator = Validator.get_coe_validator(cluster_template.coe)
    if not cluster_template.network_driver:
        cluster_template.network_driver = validator.default_network_driver
    validator.validate_network_driver(cluster_template.network_driver)


def enforce_server_type():
    @decorator.decorator
    def wrapper(func, *args, **kwargs):
        cluster_template = args[1]
        _enforce_server_type(cluster_template)
        return func(*args, **kwargs)

    return wrapper


def _enforce_server_type(cluster_template):
    validator = Validator.get_coe_validator(cluster_template.coe)
    validator.validate_server_type(cluster_template.server_type)


def enforce_volume_driver_types_create():
    @decorator.decorator
    def wrapper(func, *args, **kwargs):
        cluster_template = args[1]
        _enforce_volume_driver_types(cluster_template.as_dict())
        return func(*args, **kwargs)

    return wrapper


def enforce_volume_storage_size_create():
    @decorator.decorator
    def wrapper(func, *args, **kwargs):
        cluster_template = args[1]
        _enforce_volume_storage_size(cluster_template.as_dict())
        return func(*args, **kwargs)

    return wrapper


def enforce_volume_driver_types_update():
    @decorator.decorator
    def wrapper(func, *args, **kwargs):
        cluster_template_ident = args[1]
        patch = args[2]
        cluster_template = api_utils.get_resource('ClusterTemplate',
                                                  cluster_template_ident)
        try:
            cluster_template_dict = api_utils.apply_jsonpatch(
                cluster_template.as_dict(), patch)
        except api_utils.JSONPATCH_EXCEPTIONS as e:
            raise exception.PatchError(patch=patch, reason=e)
        _enforce_volume_driver_types(cluster_template_dict)
        return func(*args, **kwargs)

    return wrapper


def _enforce_volume_driver_types(cluster_template):
    validator = Validator.get_coe_validator(cluster_template['coe'])
    if not cluster_template.get('volume_driver'):
        return
    validator.validate_volume_driver(cluster_template['volume_driver'])


def _enforce_volume_storage_size(cluster_template):
    if not cluster_template.get('docker_volume_size'):
        return
    volume_size = cluster_template.get('docker_volume_size')
    storage_driver = cluster_template.get('docker_storage_driver')
    if storage_driver == 'devicemapper':
        if volume_size < 3:
            raise exception.InvalidParameterValue(
                'docker volume size %s GB is not valid, '
                'expecting minimum value 3GB for %s storage '
                'driver.' % (volume_size, storage_driver))


def validate_cluster_properties(delta):

    update_disallowed_properties = delta - cluster_update_allowed_properties
    if update_disallowed_properties:
        err = (_("cannot change cluster property(ies) %s.") %
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

    @classmethod
    def validate_server_type(cls, server_type):
        cls._validate_server_type(server_type)

    @classmethod
    def _validate_server_type(cls, server_type):
        """Confirm that server type is supported by Magnum for this COE."""
        if server_type not in cls.supported_server_types:
            raise exception.InvalidParameterValue(_(
                'Server type %(server_type)s is not supported, '
                'expecting a %(supported_server_types)s server type.') % {
                    'server_type': server_type,
                    'supported_server_types': '/'.join(
                        cls.supported_server_types + ['unspecified'])})


class K8sValidator(Validator):

    supported_network_drivers = ['flannel']
    supported_server_types = ['vm', 'bm']
    allowed_network_drivers = (
        CONF.cluster_template.kubernetes_allowed_network_drivers)
    default_network_driver = (
        CONF.cluster_template.kubernetes_default_network_driver)

    supported_volume_driver = ['cinder']


class SwarmValidator(Validator):

    supported_network_drivers = ['docker', 'flannel']
    supported_server_types = ['vm', 'bm']
    allowed_network_drivers = (CONF.cluster_template.
                               swarm_allowed_network_drivers)
    default_network_driver = (CONF.cluster_template.
                              swarm_default_network_driver)

    supported_volume_driver = ['rexray']


class MesosValidator(Validator):

    supported_network_drivers = ['docker']
    supported_server_types = ['vm', 'bm']
    allowed_network_drivers = (CONF.cluster_template.
                               mesos_allowed_network_drivers)
    default_network_driver = (CONF.cluster_template.
                              mesos_default_network_driver)

    supported_volume_driver = ['rexray']
