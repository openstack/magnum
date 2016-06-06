# Copyright 2013 Hewlett-Packard Development Company, L.P.
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
"""
Base classes for storage engines
"""

import abc

from oslo_config import cfg
from oslo_db import api as db_api
import six


_BACKEND_MAPPING = {'sqlalchemy': 'magnum.db.sqlalchemy.api'}
IMPL = db_api.DBAPI.from_config(cfg.CONF, backend_mapping=_BACKEND_MAPPING,
                                lazy=True)


def get_instance():
    """Return a DB API instance."""
    return IMPL


@six.add_metaclass(abc.ABCMeta)
class Connection(object):
    """Base class for storage system connections."""

    @abc.abstractmethod
    def __init__(self):
        """Constructor."""

    @abc.abstractmethod
    def get_bay_list(self, context, filters=None, limit=None,
                     marker=None, sort_key=None, sort_dir=None):
        """Get matching bays.

        Return a list of the specified columns for all bays that match the
        specified filters.

        :param context: The security context
        :param filters: Filters to apply. Defaults to None.

        :param limit: Maximum number of bays to return.
        :param marker: the last item of the previous page; we return the next
                       result set.
        :param sort_key: Attribute by which results should be sorted.
        :param sort_dir: direction in which results should be sorted.
                         (asc, desc)
        :returns: A list of tuples of the specified columns.
        """

    @abc.abstractmethod
    def create_bay(self, values):
        """Create a new bay.

        :param values: A dict containing several items used to identify
                       and track the bay, and several dicts which are passed
                       into the Drivers when managing this bay. For example:

                       ::

                        {
                         'uuid': uuidutils.generate_uuid(),
                         'name': 'example',
                         'type': 'virt'
                        }
        :returns: A bay.
        """

    @abc.abstractmethod
    def get_bay_by_id(self, context, bay_id):
        """Return a bay.

        :param context: The security context
        :param bay_id: The id of a bay.
        :returns: A bay.
        """

    @abc.abstractmethod
    def get_bay_by_uuid(self, context, bay_uuid):
        """Return a bay.

        :param context: The security context
        :param bay_uuid: The uuid of a bay.
        :returns: A bay.
        """

    @abc.abstractmethod
    def get_bay_by_name(self, context, bay_name):
        """Return a bay.

        :param context: The security context
        :param bay_name: The name of a bay.
        :returns: A bay.
        """

    @abc.abstractmethod
    def destroy_bay(self, bay_id):
        """Destroy a bay and all associated interfaces.

        :param bay_id: The id or uuid of a bay.
        """

    @abc.abstractmethod
    def update_bay(self, bay_id, values):
        """Update properties of a bay.

        :param bay_id: The id or uuid of a bay.
        :returns: A bay.
        :raises: BayNotFound
        """

    @abc.abstractmethod
    def get_baymodel_list(self, context, filters=None,
                          limit=None, marker=None, sort_key=None,
                          sort_dir=None):
        """Get matching baymodels.

        Return a list of the specified columns for all baymodels that match the
        specified filters.

        :param context: The security context
        :param filters: Filters to apply. Defaults to None.

        :param limit: Maximum number of baymodels to return.
        :param marker: the last item of the previous page; we return the next
                       result set.
        :param sort_key: Attribute by which results should be sorted.
        :param sort_dir: direction in which results should be sorted.
                         (asc, desc)
        :returns: A list of tuples of the specified columns.
        """

    @abc.abstractmethod
    def create_baymodel(self, values):
        """Create a new baymodel.

        :param values: A dict containing several items used to identify
                       and track the baymodel, and several dicts which are
                       passed into the Drivers when managing this baymodel.
                       For example:

                       ::

                        {
                         'uuid': uuidutils.generate_uuid(),
                         'name': 'example',
                         'type': 'virt'
                        }
        :returns: A baymodel.
        """

    @abc.abstractmethod
    def get_baymodel_by_id(self, context, baymodel_id):
        """Return a baymodel.

        :param context: The security context
        :param baymodel_id: The id of a baymodel.
        :returns: A baymodel.
        """

    @abc.abstractmethod
    def get_baymodel_by_uuid(self, context, baymodel_uuid):
        """Return a baymodel.

        :param context: The security context
        :param baymodel_uuid: The uuid of a baymodel.
        :returns: A baymodel.
        """

    @abc.abstractmethod
    def get_baymodel_by_name(self, context, baymodel_name):
        """Return a baymodel.

        :param context: The security context
        :param baymodel_name: The name of a baymodel.
        :returns: A baymodel.
        """

    @abc.abstractmethod
    def destroy_baymodel(self, baymodel_id):
        """Destroy a baymodel and all associated interfaces.

        :param baymodel_id: The id or uuid of a baymodel.
        """

    @abc.abstractmethod
    def update_baymodel(self, baymodel_id, values):
        """Update properties of a baymodel.

        :param baymodel_id: The id or uuid of a baymodel.
        :returns: A baymodel.
        :raises: BayModelNotFound
        """

    @abc.abstractmethod
    def get_container_list(self, context, filters=None,
                           limit=None, marker=None, sort_key=None,
                           sort_dir=None):
        """Get matching containers.

        Return a list of the specified columns for all containers that match
        the specified filters.

        :param context: The security context
        :param filters: Filters to apply. Defaults to None.

        :param limit: Maximum number of containers to return.
        :param marker: the last item of the previous page; we return the next
                       result set.
        :param sort_key: Attribute by which results should be sorted.
        :param sort_dir: direction in which results should be sorted.
                         (asc, desc)
        :returns: A list of tuples of the specified columns.
        """

    @abc.abstractmethod
    def create_container(self, values):
        """Create a new container.

        :param values: A dict containing several items used to identify
                       and track the container, and several dicts which are
                       passed
                       into the Drivers when managing this container. For
                       example:

                       ::

                        {
                         'uuid': uuidutils.generate_uuid(),
                         'name': 'example',
                         'type': 'virt'
                        }
        :returns: A container.
        """

    @abc.abstractmethod
    def get_container_by_id(self, context, container_id):
        """Return a container.

        :param context: The security context
        :param container_id: The id of a container.
        :returns: A container.
        """

    @abc.abstractmethod
    def get_container_by_uuid(self, context, container_uuid):
        """Return a container.

        :param context: The security context
        :param container_uuid: The uuid of a container.
        :returns: A container.
        """

    @abc.abstractmethod
    def get_container_by_name(self, context, container_name):
        """Return a container.

        :param context: The security context
        :param container_name: The name of a container.
        :returns: A container.
        """

    @abc.abstractmethod
    def destroy_container(self, container_id):
        """Destroy a container and all associated interfaces.

        :param container_id: The id or uuid of a container.
        """

    @abc.abstractmethod
    def update_container(self, container_id, values):
        """Update properties of a container.

        :param container_id: The id or uuid of a container.
        :returns: A container.
        :raises: ContainerNotFound
        """

    @abc.abstractmethod
    def get_rc_list(self, context, filters=None, limit=None,
                    marker=None, sort_key=None, sort_dir=None):
        """Get matching ReplicationControllers.

        Return a list of the specified columns for all rcs that match the
        specified filters.

        :param context: The security context
        :param filters: Filters to apply. Defaults to None.

        :param limit: Maximum number of pods to return.
        :param marker: the last item of the previous page; we return the next
                       result set.
        :param sort_key: Attribute by which results should be sorted.
        :param sort_dir: direction in which results should be sorted.
                         (asc, desc)
        :returns: A list of tuples of the specified columns.
        """

    @abc.abstractmethod
    def create_rc(self, values):
        """Create a new ReplicationController.

        :param values: A dict containing several items used to identify
                       and track the rc, and several dicts which are passed
                       into the Drivers when managing this pod. For example:

                       ::

                        {
                         'uuid': uuidutils.generate_uuid(),
                         'name': 'example',
                         'images': '["myimage"]'
                        }
        :returns: A ReplicationController.
        """

    @abc.abstractmethod
    def get_rc_by_id(self, context, rc_id):
        """Return a ReplicationController.

        :param context: The security context
        :param rc_id: The id of a rc.
        :returns: A ReplicationController.
        """

    @abc.abstractmethod
    def get_rc_by_uuid(self, context, rc_uuid):
        """Return a ReplicationController.

        :param context: The security context
        :param rc_uuid: The uuid of a ReplicationController.
        :returns: A ReplicationController.
        """

    @abc.abstractmethod
    def get_rc_by_name(self, context, rc_name):
        """Return a ReplicationController.

        :param context: The security context
        :param rc_name: The name of a ReplicationController.
        :returns: A ReplicationController.
        """

    @abc.abstractmethod
    def destroy_rc(self, rc_id):
        """Destroy a ReplicationController and all associated interfaces.

        :param rc_id: The id or uuid of a ReplicationController.
        """

    @abc.abstractmethod
    def update_rc(self, rc_id, values):
        """Update properties of a ReplicationController.

        :param rc_id: The id or uuid of a ReplicationController.
        :returns: A ReplicationController.
        """

    @abc.abstractmethod
    def create_x509keypair(self, values):
        """Create a new x509keypair.

        :param values: A dict containing several items used to identify
                       and track the x509keypair, and several dicts which
                       are passed into the Drivers when managing this
                       x509keypair. For example:

                       ::

                        {
                         'uuid': uuidutils.generate_uuid(),
                         'certificate': 'AAA...',
                         'private_key': 'BBB...',
                         'private_key_passphrase': 'CCC...',
                         'intermediates': 'DDD...',
                        }
        :returns: A X509KeyPair.
        """

    @abc.abstractmethod
    def get_x509keypair_by_id(self, context, x509keypair_id):
        """Return a x509keypair.

        :param context: The security context
        :param x509keypair_id: The id of a x509keypair.
        :returns: A x509keypair.
        """

    @abc.abstractmethod
    def get_x509keypair_by_uuid(self, context, x509keypair_uuid):
        """Return a x509keypair.

        :param context: The security context
        :param x509keypair_uuid: The uuid of a x509keypair.
        :returns: A x509keypair.
        """

    @abc.abstractmethod
    def destroy_x509keypair(self, x509keypair_id):
        """Destroy a x509keypair.

        :param x509keypair_id: The id or uuid of a x509keypair.
        """

    @abc.abstractmethod
    def update_x509keypair(self, x509keypair_id, values):
        """Update properties of a X509KeyPair.

        :param x509keypair_id: The id or uuid of a X509KeyPair.
        :returns: A X509KeyPair.
        """

    @abc.abstractmethod
    def get_x509keypair_list(self, context, filters=None, limit=None,
                             marker=None, sort_key=None, sort_dir=None):
        """Get matching x509keypairs.

        Return a list of the specified columns for all x509keypairs
        that match the specified filters.

        :param context: The security context
        :param filters: Filters to apply. Defaults to None.

        :param limit: Maximum number of x509keypairs to return.
        :param marker: the last item of the previous page; we return the next
                       result set.
        :param sort_key: Attribute by which results should be sorted.
        :param sort_dir: direction in which results should be sorted.
                         (asc, desc)
        :returns: A list of tuples of the specified columns.
        """

    @abc.abstractmethod
    def destroy_magnum_service(self, magnum_service_id):
        """Destroys a magnum_service record.

        :param magnum_service_id: The id of a magnum_service.
        """

    @abc.abstractmethod
    def update_magnum_service(self, magnum_service_id, values):
        """Update properties of a magnum_service.

        :param magnum_service_id: The id of a magnum_service record.
        """

    @abc.abstractmethod
    def get_magnum_service_by_host_and_binary(self, context, host, binary):
        """Return a magnum_service record.

        :param context: The security context
        :param host: The host where the binary is located.
        :param binary: The name of the binary.
        :returns: A magnum_service record.
        """

    @abc.abstractmethod
    def create_magnum_service(self, values):
        """Create a new magnum_service record.

        :param values: A dict containing several items used to identify
                       and define the magnum_service record.
        :returns: A magnum_service record.
        """

    @abc.abstractmethod
    def get_magnum_service_list(self, context, disabled=None, limit=None,
                                marker=None, sort_key=None, sort_dir=None):
        """Get matching magnum_service records.

        Return a list of the specified columns for all magnum_services
        those match the specified filters.

        :param context: The security context
        :param disabled: Filters disbaled services. Defaults to None.
        :param limit: Maximum number of magnum_services to return.
        :param marker: the last item of the previous page; we return the next
                       result set.
        :param sort_key: Attribute by which results should be sorted.
        :param sort_dir: direction in which results should be sorted.
                         (asc, desc)
        :returns: A list of tuples of the specified columns.
        """

    @abc.abstractmethod
    def create_quota(self, values):
        """Create a new Quota record for a resource in a project.

        :param values: A dict containing several items used to identify
                       and track quota for a resource in a project.

                       ::

                        {
                         'id': uuidutils.generate_uuid(),
                         'project_id': 'fake_project',
                         'resource': 'fake_resource',
                         'hard_limit': 'fake_hardlimit',
                        }

        :returns: A quota record.
        """

    @abc.abstractmethod
    def quota_get_all_by_project_id(self, project_id):
        """Gets Quota record for all the resources in a project.

        :param project_id: Project identifier of the project.

        :returns: Quota record for all resources in a project.
        """
