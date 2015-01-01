# -*- encoding: utf-8 -*-
#
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

from oslo.config import cfg
from oslo.db import api as db_api
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
    def get_bay_list(self, columns=None, filters=None, limit=None,
                     marker=None, sort_key=None, sort_dir=None):
        """Get specific columns for matching bays.

        Return a list of the specified columns for all bays that match the
        specified filters.

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
    def reserve_bay(self, tag, bay_id):
        """Reserve a bay.

        To prevent other ManagerServices from manipulating the given
        Bay while a Task is performed, mark it reserved by this host.

        :param tag: A string uniquely identifying the reservation holder.
        :param bay_id: A bay id or uuid.
        :returns: A Bay object.
        :raises: BayNotFound if the bay is not found.
        :raises: BayLocked if the bay is already reserved.
        """

    @abc.abstractmethod
    def release_bay(self, tag, bay_id):
        """Release the reservation on a bay.

        :param tag: A string uniquely identifying the reservation holder.
        :param bay_id: A bay id or uuid.
        :raises: BayNotFound if the bay is not found.
        :raises: BayLocked if the bay is reserved by another host.
        :raises: BayNotLocked if the bay was found to not have a
                 reservation at all.
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
    def get_bay_by_id(self, bay_id):
        """Return a bay.

        :param bay_id: The id of a bay.
        :returns: A bay.
        """

    @abc.abstractmethod
    def get_bay_by_uuid(self, bay_uuid):
        """Return a bay.

        :param bay_uuid: The uuid of a bay.
        :returns: A bay.
        """

    @abc.abstractmethod
    def get_bay_by_instance(self, instance):
        """Return a bay.

        :param instance: The instance name or uuid to search for.
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
        :raises: BayAssociated
        :raises: BayNotFound
        """

    @abc.abstractmethod
    def get_baymodel_list(self, columns=None, filters=None, limit=None,
                     marker=None, sort_key=None, sort_dir=None):
        """Get specific columns for matching baymodels.

        Return a list of the specified columns for all baymodels that match the
        specified filters.

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
    def get_baymodel_by_id(self, baymodel_id):
        """Return a baymodel.

        :param baymodel_id: The id of a baymodel.
        :returns: A baymodel.
        """

    @abc.abstractmethod
    def get_baymodel_by_uuid(self, baymodel_uuid):
        """Return a baymodel.

        :param baymodel_uuid: The uuid of a baymodel.
        :returns: A baymodel.
        """

    @abc.abstractmethod
    def get_baymodel_by_instance(self, instance):
        """Return a baymodel.

        :param instance: The instance name or uuid to search for.
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
    def get_container_list(self, columns=None, filters=None, limit=None,
                     marker=None, sort_key=None, sort_dir=None):
        """Get specific columns for matching containers.

        Return a list of the specified columns for all containers that match
        the specified filters.

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
    def reserve_container(self, tag, container_id):
        """Reserve a container.

        To prevent other ManagerServices from manipulating the given
        Bay while a Task is performed, mark it reserved by this host.

        :param tag: A string uniquely identifying the reservation holder.
        :param container_id: A container id or uuid.
        :returns: A Bay object.
        :raises: BayNotFound if the container is not found.
        :raises: BayLocked if the container is already reserved.
        """

    @abc.abstractmethod
    def release_container(self, tag, container_id):
        """Release the reservation on a container.

        :param tag: A string uniquely identifying the reservation holder.
        :param container_id: A container id or uuid.
        :raises: BayNotFound if the container is not found.
        :raises: BayLocked if the container is reserved by another host.
        :raises: BayNotLocked if the container was found to not have a
                 reservation at all.
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
    def get_container_by_id(self, container_id):
        """Return a container.

        :param container_id: The id of a container.
        :returns: A container.
        """

    @abc.abstractmethod
    def get_container_by_uuid(self, container_uuid):
        """Return a container.

        :param container_uuid: The uuid of a container.
        :returns: A container.
        """

    @abc.abstractmethod
    def get_container_by_instance(self, instance):
        """Return a container.

        :param instance: The instance name or uuid to search for.
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
        :raises: BayAssociated
        :raises: BayNotFound
        """

    @abc.abstractmethod
    def get_node_list(self, columns=None, filters=None, limit=None,
                     marker=None, sort_key=None, sort_dir=None):
        """Get specific columns for matching nodes.

        Return a list of the specified columns for all nodes that match the
        specified filters.

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
    def reserve_node(self, tag, node_id):
        """Reserve a node.

        To prevent other ManagerServices from manipulating the given
        Node while a Task is performed, mark it reserved by this host.

        :param tag: A string uniquely identifying the reservation holder.
        :param node_id: A node id or uuid.
        :returns: A Node object.
        :raises: NodeNotFound if the node is not found.
        :raises: NodeLocked if the node is already reserved.
        """

    @abc.abstractmethod
    def release_node(self, tag, node_id):
        """Release the reservation on a node.

        :param tag: A string uniquely identifying the reservation holder.
        :param node_id: A node id or uuid.
        :raises: NodeNotFound if the node is not found.
        :raises: NodeLocked if the node is reserved by another host.
        :raises: NodeNotLocked if the node was found to not have a
                 reservation at all.
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
    def get_node_by_id(self, node_id):
        """Return a node.

        :param node_id: The id of a node.
        :returns: A node.
        """

    @abc.abstractmethod
    def get_node_by_uuid(self, node_uuid):
        """Return a node.

        :param node_uuid: The uuid of a node.
        :returns: A node.
        """

    @abc.abstractmethod
    def get_node_by_instance(self, instance):
        """Return a node.

        :param instance: The instance name or uuid to search for.
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
    def get_pod_list(self, columns=None, filters=None, limit=None,
                     marker=None, sort_key=None, sort_dir=None):
        """Get specific columns for matching pods.

        Return a list of the specified columns for all pods that match the
        specified filters.

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
    def reserve_pod(self, tag, pod_id):
        """Reserve a pod.

        To prevent other ManagerServices from manipulating the given
        Bay while a Task is performed, mark it reserved by this host.

        :param tag: A string uniquely identifying the reservation holder.
        :param pod_id: A pod id or uuid.
        :returns: A Bay object.
        :raises: BayNotFound if the pod is not found.
        :raises: BayLocked if the pod is already reserved.
        """

    @abc.abstractmethod
    def release_pod(self, tag, pod_id):
        """Release the reservation on a pod.

        :param tag: A string uniquely identifying the reservation holder.
        :param pod_id: A pod id or uuid.
        :raises: BayNotFound if the pod is not found.
        :raises: BayLocked if the pod is reserved by another host.
        :raises: BayNotLocked if the pod was found to not have a
                 reservation at all.
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
    def get_pod_by_id(self, pod_id):
        """Return a pod.

        :param pod_id: The id of a pod.
        :returns: A pod.
        """

    @abc.abstractmethod
    def get_pod_by_uuid(self, pod_uuid):
        """Return a pod.

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
    def get_pod_by_instance(self, instance):
        """Return a pod.

        :param instance: The instance name or uuid to search for.
        :returns: A pod.
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
        :raises: BayAssociated
        :raises: BayNotFound
        """

    @abc.abstractmethod
    def get_service_list(self, columns=None, filters=None, limit=None,
                     marker=None, sort_key=None, sort_dir=None):
        """Get specific columns for matching services.

        Return a list of the specified columns for all services that match the
        specified filters.

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
    def reserve_service(self, tag, service_id):
        """Reserve a service.

        To prevent other ManagerServices from manipulating the given
        Bay while a Task is performed, mark it reserved by this host.

        :param tag: A string uniquely identifying the reservation holder.
        :param service_id: A service id or uuid.
        :returns: A Bay object.
        :raises: BayNotFound if the service is not found.
        :raises: BayLocked if the service is already reserved.
        """

    @abc.abstractmethod
    def release_service(self, tag, service_id):
        """Release the reservation on a service.

        :param tag: A string uniquely identifying the reservation holder.
        :param service_id: A service id or uuid.
        :raises: BayNotFound if the service is not found.
        :raises: BayLocked if the service is reserved by another host.
        :raises: BayNotLocked if the service was found to not have a
                 reservation at all.
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
    def get_service_by_id(self, service_id):
        """Return a service.

        :param service_id: The id of a service.
        :returns: A service.
        """

    @abc.abstractmethod
    def get_service_by_uuid(self, service_uuid):
        """Return a service.

        :param service_uuid: The uuid of a service.
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
        :raises: BayAssociated
        :raises: BayNotFound
        """
