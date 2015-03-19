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
    def get_bay_list(self, context, columns=None, filters=None, limit=None,
                     marker=None, sort_key=None, sort_dir=None):
        """Get specific columns for matching bays.

        Return a list of the specified columns for all bays that match the
        specified filters.

        :param context: The security context
        :param columns: List of column names to return.
                        Defaults to 'id' column when columns == None.
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
                         'uuid': utils.generate_uuid(),
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
    def get_baymodel_list(self, context, columns=None, filters=None,
                          limit=None, marker=None, sort_key=None,
                          sort_dir=None):
        """Get specific columns for matching baymodels.

        Return a list of the specified columns for all baymodels that match the
        specified filters.

        :param context: The security context
        :param columns: List of column names to return.
                        Defaults to 'id' column when columns == None.
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
                         'uuid': utils.generate_uuid(),
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
    def get_container_list(self, context, columns=None, filters=None,
                           limit=None, marker=None, sort_key=None,
                           sort_dir=None):
        """Get specific columns for matching containers.

        Return a list of the specified columns for all containers that match
        the specified filters.

        :param context: The security context
        :param columns: List of column names to return.
                        Defaults to 'id' column when columns == None.
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
                         'uuid': utils.generate_uuid(),
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
    def destroy_container(self, container_id):
        """Destroy a container and all associated interfaces.

        :param container_id: The id or uuid of a container.
        """

    @abc.abstractmethod
    def update_container(self, container_id, values):
        """Update properties of a container.

        :param container_id: The id or uuid of a container.
        :returns: A container.
        :raises: BayNotFound
        """

    @abc.abstractmethod
    def get_node_list(self, context, columns=None, filters=None, limit=None,
                     marker=None, sort_key=None, sort_dir=None):
        """Get specific columns for matching nodes.

        Return a list of the specified columns for all nodes that match the
        specified filters.

        :param context: The security context
        :param columns: List of column names to return.
                        Defaults to 'id' column when columns == None.
        :param filters: Filters to apply. Defaults to None.

        :param limit: Maximum number of nodes to return.
        :param marker: the last item of the previous page; we return the next
                       result set.
        :param sort_key: Attribute by which results should be sorted.
        :param sort_dir: direction in which results should be sorted.
                         (asc, desc)
        :returns: A list of tuples of the specified columns.
        """

    @abc.abstractmethod
    def create_node(self, values):
        """Create a new node.

        :param values: A dict containing several items used to identify
                       and track the node, and several dicts which are passed
                       into the Drivers when managing this node. For example:

                       ::

                        {
                         'uuid': utils.generate_uuid(),
                         'name': 'example',
                         'type': 'virt'
                        }
        :returns: A node.
        """

    @abc.abstractmethod
    def get_node_by_id(self, context, node_id):
        """Return a node.

        :param context: The security context
        :param node_id: The id of a node.
        :returns: A node.
        """

    @abc.abstractmethod
    def get_node_by_uuid(self, context, node_uuid):
        """Return a node.

        :param context: The security context
        :param node_uuid: The uuid of a node.
        :returns: A node.
        """

    @abc.abstractmethod
    def destroy_node(self, node_id):
        """Destroy a node and all associated interfaces.

        :param node_id: The id or uuid of a node.
        """

    @abc.abstractmethod
    def update_node(self, node_id, values):
        """Update properties of a node.

        :param node_id: The id or uuid of a node.
        :returns: A node.
        :raises: NodeAssociated
        :raises: NodeNotFound
        """
    @abc.abstractmethod
    def get_pod_list(self, context, columns=None, filters=None, limit=None,
                     marker=None, sort_key=None, sort_dir=None):
        """Get specific columns for matching pods.

        Return a list of the specified columns for all pods that match the
        specified filters.

        :param context: The security context
        :param columns: List of column names to return.
                        Defaults to 'id' column when columns == None.
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
    def create_pod(self, values):
        """Create a new pod.

        :param values: A dict containing several items used to identify
                       and track the pod, and several dicts which are passed
                       into the Drivers when managing this pod. For example:

                       ::

                        {
                         'uuid': utils.generate_uuid(),
                         'name': 'example',
                         'type': 'virt'
                        }
        :returns: A pod.
        """

    @abc.abstractmethod
    def get_pod_by_id(self, context, pod_id):
        """Return a pod.

        :param context: The security context
        :param pod_id: The id of a pod.
        :returns: A pod.
        """

    @abc.abstractmethod
    def get_pod_by_uuid(self, context, pod_uuid):
        """Return a pod.

        :param context: The security context
        :param pod_uuid: The uuid of a pod.
        :returns: A pod.
        """

    @abc.abstractmethod
    def get_pod_by_name(self, pod_name):
        """Return a pod.

        :param pod_name: The name of a pod.
        :returns: A pod.
        """

    @abc.abstractmethod
    def get_pods_by_bay_uuid(self, bay_uuid):
        """List all the pods for a given bay.

        :param bay_uuid: The uuid of a bay.
        :returns: A list of pods.
        """

    @abc.abstractmethod
    def destroy_pod(self, pod_id):
        """Destroy a pod and all associated interfaces.

        :param pod_id: The id or uuid of a pod.
        """

    @abc.abstractmethod
    def update_pod(self, pod_id, values):
        """Update properties of a pod.

        :param pod_id: The id or uuid of a pod.
        :returns: A pod.
        :raises: BayNotFound
        """

    @abc.abstractmethod
    def get_service_list(self, context, columns=None, filters=None, limit=None,
                     marker=None, sort_key=None, sort_dir=None):
        """Get specific columns for matching services.

        Return a list of the specified columns for all services that match the
        specified filters.

        :param context: The security context
        :param columns: List of column names to return.
                        Defaults to 'id' column when columns == None.
        :param filters: Filters to apply. Defaults to None.

        :param limit: Maximum number of services to return.
        :param marker: the last item of the previous page; we return the next
                       result set.
        :param sort_key: Attribute by which results should be sorted.
        :param sort_dir: direction in which results should be sorted.
                         (asc, desc)
        :returns: A list of tuples of the specified columns.
        """

    @abc.abstractmethod
    def create_service(self, values):
        """Create a new service.

        :param values: A dict containing several items used to identify
                       and track the service, and several dicts which are
                       passed into the Drivers when managing this service.
                       For example:

                       ::

                        {
                         'uuid': utils.generate_uuid(),
                         'name': 'example',
                         'type': 'virt'
                        }
        :returns: A service.
        """

    @abc.abstractmethod
    def get_service_by_id(self, context, service_id):
        """Return a service.

        :param context: The security context
        :param service_id: The id of a service.
        :returns: A service.
        """

    @abc.abstractmethod
    def get_service_by_uuid(self, context, service_uuid):
        """Return a service.

        :param context: The security context
        :param service_uuid: The uuid of a service.
        :returns: A service.
        """

    @abc.abstractmethod
    def get_services_by_bay_uuid(self, bay_uuid):
        """List all the services for a given bay.

        :param bay_uuid: The uuid of a bay.
        :returns: A list of services.
        """

    @abc.abstractmethod
    def get_service_by_name(self, bay_name):
        """Return a service.

        :param context: The security context
        :param service_name: The name of a service
        :returns: A service.
        """

    @abc.abstractmethod
    def destroy_service(self, service_id):
        """Destroy a service and all associated interfaces.

        :param service_id: The id or uuid of a service.
        """

    @abc.abstractmethod
    def update_service(self, service_id, values):
        """Update properties of a service.

        :param service_id: The id or uuid of a service.
        :returns: A service.
        :raises: BayNotFound
        """

    @abc.abstractmethod
    def get_rc_list(self, context, columns=None, filters=None, limit=None,
                     marker=None, sort_key=None, sort_dir=None):
        """Get specific columns for matching ReplicationController.

        Return a list of the specified columns for all rcs that match the
        specified filters.

        :param context: The security context
        :param columns: List of column names to return.
                        Defaults to 'id' column when columns == None.
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
    def get_rcs_by_bay_uuid(self, bay_uuid):
        """List all the ReplicationControllers for a given bay.

        :param bay_uuid: The uuid of a bay.
        :returns: A list of ReplicationControllers.
        """

    @abc.abstractmethod
    def create_rc(self, values):
        """Create a new ReplicationController.

        :param values: A dict containing several items used to identify
                       and track the rc, and several dicts which are passed
                       into the Drivers when managing this pod. For example:

                       ::

                        {
                         'uuid': utils.generate_uuid(),
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
    def get_rc_by_name(self, rc_name):
        """Return a ReplicationController.

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
