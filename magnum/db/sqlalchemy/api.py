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

"""SQLAlchemy storage backend."""

import datetime

from oslo.config import cfg
from oslo.db import exception as db_exc
from oslo.db.sqlalchemy import session as db_session
from oslo.db.sqlalchemy import utils as db_utils
from oslo.utils import timeutils
from sqlalchemy.orm.exc import NoResultFound

from magnum.common import exception
from magnum.common import utils
from magnum.db import api
from magnum.db.sqlalchemy import models
from magnum.openstack.common._i18n import _
from magnum.openstack.common import log

CONF = cfg.CONF

LOG = log.getLogger(__name__)


_FACADE = None


def _create_facade_lazily():
    global _FACADE
    if _FACADE is None:
        _FACADE = db_session.EngineFacade.from_config(CONF)
    return _FACADE


def get_engine():
    facade = _create_facade_lazily()
    return facade.get_engine()


def get_session(**kwargs):
    facade = _create_facade_lazily()
    return facade.get_session(**kwargs)


def get_backend():
    """The backend is this module itself."""
    return Connection()


def model_query(model, *args, **kwargs):
    """Query helper for simpler session usage.

    :param session: if present, the session to use
    """

    session = kwargs.get('session') or get_session()
    query = session.query(model, *args)
    return query


def add_identity_filter(query, value):
    """Adds an identity filter to a query.

    Filters results by ID, if supplied value is a valid integer.
    Otherwise attempts to filter results by UUID.

    :param query: Initial query to add filter to.
    :param value: Value for filtering results by.
    :return: Modified query.
    """
    if utils.is_int_like(value):
        return query.filter_by(id=value)
    elif utils.is_uuid_like(value):
        return query.filter_by(uuid=value)
    else:
        raise exception.InvalidIdentity(identity=value)


def _check_port_change_forbidden(port, session):
    bay_id = port['bay_id']
    if bay_id is not None:
        query = model_query(models.Bay, session=session)
        query = query.filter_by(id=bay_id)
        bay_ref = query.one()
        if bay_ref['reservation'] is not None:
            raise exception.BayLocked(bay=bay_ref['uuid'],
                                       host=bay_ref['reservation'])


def _paginate_query(model, limit=None, marker=None, sort_key=None,
                    sort_dir=None, query=None):
    if not query:
        query = model_query(model)
    sort_keys = ['id']
    if sort_key and sort_key not in sort_keys:
        sort_keys.insert(0, sort_key)
    query = db_utils.paginate_query(query, model, limit, sort_keys,
                                    marker=marker, sort_dir=sort_dir)
    return query.all()


class Connection(api.Connection):
    """SqlAlchemy connection."""

    def __init__(self):
        pass

    def _add_bays_filters(self, query, filters):
        if filters is None:
            filters = []

        if 'associated' in filters:
            if filters['associated']:
                query = query.filter(models.Bay.instance_uuid is not None)
            else:
                query = query.filter(models.Bay.instance_uuid is None)
        if 'reserved' in filters:
            if filters['reserved']:
                query = query.filter(models.Bay.reservation is not None)
            else:
                query = query.filter(models.Bay.reservation is None)
        if 'maintenance' in filters:
            query = query.filter_by(maintenance=filters['maintenance'])
        if 'driver' in filters:
            query = query.filter_by(driver=filters['driver'])
        if 'provision_state' in filters:
            query = query.filter_by(provision_state=filters['provision_state'])
        if 'provisioned_before' in filters:
            limit = timeutils.utcnow() - datetime.timedelta(
                                         seconds=filters['provisioned_before'])
            query = query.filter(models.Bay.provision_updated_at < limit)

        return query

    def get_bayinfo_list(self, columns=None, filters=None, limit=None,
                          marker=None, sort_key=None, sort_dir=None):
        # list-ify columns default values because it is bad form
        # to include a mutable list in function definitions.
        if columns is None:
            columns = [models.Bay.id]
        else:
            columns = [getattr(models.Bay, c) for c in columns]

        query = model_query(*columns, base_model=models.Bay)
        query = self._add_bays_filters(query, filters)
        return _paginate_query(models.Bay, limit, marker,
                               sort_key, sort_dir, query)

    def get_bay_list(self, filters=None, limit=None, marker=None,
                      sort_key=None, sort_dir=None):
        query = model_query(models.Bay)
        query = self._add_bays_filters(query, filters)
        return _paginate_query(models.Bay, limit, marker,
                               sort_key, sort_dir, query)

    def reserve_bay(self, tag, bay_id):
        session = get_session()
        with session.begin():
            query = model_query(models.Bay, session=session)
            query = add_identity_filter(query, bay_id)
            # be optimistic and assume we usually create a reservation
            count = query.filter_by(reservation=None).update(
                        {'reservation': tag}, synchronize_session=False)
            try:
                bay = query.one()
                if count != 1:
                    # Nothing updated and bay exists. Must already be
                    # locked.
                    raise exception.BayLocked(bay=bay_id,
                                               host=bay['reservation'])
                return bay
            except NoResultFound:
                raise exception.BayNotFound(bay_id)

    def release_bay(self, tag, bay_id):
        session = get_session()
        with session.begin():
            query = model_query(models.Bay, session=session)
            query = add_identity_filter(query, bay_id)
            # be optimistic and assume we usually release a reservation
            count = query.filter_by(reservation=tag).update(
                        {'reservation': None}, synchronize_session=False)
            try:
                if count != 1:
                    bay = query.one()
                    if bay['reservation'] is None:
                        raise exception.BayNotLocked(bay=bay_id)
                    else:
                        raise exception.BayLocked(bay=bay_id,
                                                   host=bay['reservation'])
            except NoResultFound:
                raise exception.BayNotFound(bay_id)

    def create_bay(self, values):
        # ensure defaults are present for new bays
        if not values.get('uuid'):
            values['uuid'] = utils.generate_uuid()

        bay = models.Bay()
        bay.update(values)
        try:
            bay.save()
        except db_exc.DBDuplicateEntry as exc:
            if 'instance_uuid' in exc.columns:
                raise exception.InstanceAssociated(
                    instance_uuid=values['instance_uuid'],
                    bay=values['uuid'])
            raise exception.BayAlreadyExists(uuid=values['uuid'])
        return bay

    def get_bay_by_id(self, bay_id):
        query = model_query(models.Bay).filter_by(id=bay_id)
        try:
            return query.one()
        except NoResultFound:
            raise exception.BayNotFound(bay=bay_id)

    def get_bay_by_uuid(self, bay_uuid):
        query = model_query(models.Bay).filter_by(uuid=bay_uuid)
        try:
            return query.one()
        except NoResultFound:
            raise exception.BayNotFound(bay=bay_uuid)

    def get_bay_by_instance(self, instance):
        if not utils.is_uuid_like(instance):
            raise exception.InvalidUUID(uuid=instance)

        query = (model_query(models.Bay)
                 .filter_by(instance_uuid=instance))

        try:
            result = query.one()
        except NoResultFound:
            raise exception.InstanceNotFound(instance=instance)

        return result

    def destroy_bay(self, bay_id):
        session = get_session()
        with session.begin():
            query = model_query(models.Bay, session=session)
            query = add_identity_filter(query, bay_id)
            query.delete()

    def update_bay(self, bay_id, values):
        # NOTE(dtantsur): this can lead to very strange errors
        if 'uuid' in values:
            msg = _("Cannot overwrite UUID for an existing Bay.")
            raise exception.InvalidParameterValue(err=msg)

        try:
            return self._do_update_bay(bay_id, values)
        except db_exc.DBDuplicateEntry:
            raise exception.InstanceAssociated(
                instance_uuid=values['instance_uuid'],
                bay=bay_id)

    def _do_update_bay(self, bay_id, values):
        session = get_session()
        with session.begin():
            query = model_query(models.Bay, session=session)
            query = add_identity_filter(query, bay_id)
            try:
                ref = query.with_lockmode('update').one()
            except NoResultFound:
                raise exception.BayNotFound(bay=bay_id)

            # Prevent instance_uuid overwriting
            if values.get("instance_uuid") and ref.instance_uuid:
                raise exception.BayAssociated(bay=bay_id,
                                instance=ref.instance_uuid)

            if 'provision_state' in values:
                values['provision_updated_at'] = timeutils.utcnow()

            ref.update(values)
        return ref

    def _add_containers_filters(self, query, filters):
        if filters is None:
            filters = []

        if 'associated' in filters:
            if filters['associated']:
                query = query.filter(models.Container.instance_uuid is not
                    None)
            else:
                query = query.filter(models.Container.instance_uuid is None)
        if 'reserved' in filters:
            if filters['reserved']:
                query = query.filter(models.Container.reservation is not None)
            else:
                query = query.filter(models.Container.reservation is None)
        if 'maintenance' in filters:
            query = query.filter_by(maintenance=filters['maintenance'])
        if 'driver' in filters:
            query = query.filter_by(driver=filters['driver'])
        if 'provision_state' in filters:
            query = query.filter_by(provision_state=filters['provision_state'])
        if 'provisioned_before' in filters:
            limit = timeutils.utcnow() - datetime.timedelta(
                                         seconds=filters['provisioned_before'])
            query = query.filter(models.Container.provision_updated_at < limit)

        return query

    def get_containerinfo_list(self, columns=None, filters=None, limit=None,
                          marker=None, sort_key=None, sort_dir=None):
        # list-ify columns default values because it is bad form
        # to include a mutable list in function definitions.
        if columns is None:
            columns = [models.Container.id]
        else:
            columns = [getattr(models.Container, c) for c in columns]

        query = model_query(*columns, base_model=models.Container)
        query = self._add_containers_filters(query, filters)
        return _paginate_query(models.Container, limit, marker,
                               sort_key, sort_dir, query)

    def get_container_list(self, filters=None, limit=None, marker=None,
                      sort_key=None, sort_dir=None):
        query = model_query(models.Container)
        query = self._add_containers_filters(query, filters)
        return _paginate_query(models.Container, limit, marker,
                               sort_key, sort_dir, query)

    def reserve_container(self, tag, container_id):
        session = get_session()
        with session.begin():
            query = model_query(models.Container, session=session)
            query = add_identity_filter(query, container_id)
            # be optimistic and assume we usually create a reservation
            count = query.filter_by(reservation=None).update(
                        {'reservation': tag}, synchronize_session=False)
            try:
                container = query.one()
                if count != 1:
                    # Nothing updated and container exists. Must already be
                    # locked.
                    raise exception.ContainerLocked(container=container_id,
                                               host=container['reservation'])
                return container
            except NoResultFound:
                raise exception.ContainerNotFound(container_id)

    def release_container(self, tag, container_id):
        session = get_session()
        with session.begin():
            query = model_query(models.Container, session=session)
            query = add_identity_filter(query, container_id)
            # be optimistic and assume we usually release a reservation
            count = query.filter_by(reservation=tag).update(
                        {'reservation': None}, synchronize_session=False)
            try:
                if count != 1:
                    container = query.one()
                    if container['reservation'] is None:
                        raise exception.ContainerNotLocked(
                            container=container_id)
                    else:
                        raise exception.ContainerLocked(container=container_id,
                            host=container['reservation'])
            except NoResultFound:
                raise exception.ContainerNotFound(container_id)

    def create_container(self, values):
        # ensure defaults are present for new containers
        if not values.get('uuid'):
            values['uuid'] = utils.generate_uuid()

        container = models.Container()
        container.update(values)
        try:
            container.save()
        except db_exc.DBDuplicateEntry as exc:
            if 'instance_uuid' in exc.columns:
                raise exception.InstanceAssociated(
                    instance_uuid=values['instance_uuid'],
                    container=values['uuid'])
            raise exception.ContainerAlreadyExists(uuid=values['uuid'])
        return container

    def get_container_by_id(self, container_id):
        query = model_query(models.Container).filter_by(id=container_id)
        try:
            return query.one()
        except NoResultFound:
            raise exception.ContainerNotFound(container=container_id)

    def get_container_by_uuid(self, container_uuid):
        query = model_query(models.Container).filter_by(uuid=container_uuid)
        try:
            return query.one()
        except NoResultFound:
            raise exception.ContainerNotFound(container=container_uuid)

    def get_container_by_instance(self, instance):
        if not utils.is_uuid_like(instance):
            raise exception.InvalidUUID(uuid=instance)

        query = (model_query(models.Container)
                 .filter_by(instance_uuid=instance))

        try:
            result = query.one()
        except NoResultFound:
            raise exception.InstanceNotFound(instance=instance)

        return result

    def destroy_container(self, container_id):
        session = get_session()
        with session.begin():
            query = model_query(models.Container, session=session)
            query = add_identity_filter(query, container_id)
            query.delete()

    def update_container(self, container_id, values):
        # NOTE(dtantsur): this can lead to very strange errors
        if 'uuid' in values:
            msg = _("Cannot overwrite UUID for an existing Container.")
            raise exception.InvalidParameterValue(err=msg)

        try:
            return self._do_update_container(container_id, values)
        except db_exc.DBDuplicateEntry:
            raise exception.InstanceAssociated(
                instance_uuid=values['instance_uuid'],
                container=container_id)

    def _do_update_container(self, container_id, values):
        session = get_session()
        with session.begin():
            query = model_query(models.Container, session=session)
            query = add_identity_filter(query, container_id)
            try:
                ref = query.with_lockmode('update').one()
            except NoResultFound:
                raise exception.ContainerNotFound(container=container_id)

            # Prevent instance_uuid overwriting
            if values.get("instance_uuid") and ref.instance_uuid:
                raise exception.ContainerAssociated(container=container_id,
                                instance=ref.instance_uuid)

            if 'provision_state' in values:
                values['provision_updated_at'] = timeutils.utcnow()

            ref.update(values)
        return ref

    def _add_nodes_filters(self, query, filters):
        if filters is None:
            filters = []

        if 'associated' in filters:
            if filters['associated']:
                query = query.filter(models.Node.instance_uuid is not None)
            else:
                query = query.filter(models.Node.instance_uuid is None)
        if 'reserved' in filters:
            if filters['reserved']:
                query = query.filter(models.Node.reservation is not None)
            else:
                query = query.filter(models.Node.reservation is None)
        if 'maintenance' in filters:
            query = query.filter_by(maintenance=filters['maintenance'])
        if 'driver' in filters:
            query = query.filter_by(driver=filters['driver'])
        if 'provision_state' in filters:
            query = query.filter_by(provision_state=filters['provision_state'])
        if 'provisioned_before' in filters:
            limit = timeutils.utcnow() - datetime.timedelta(
                                         seconds=filters['provisioned_before'])
            query = query.filter(models.Node.provision_updated_at < limit)

        return query

    def get_nodeinfo_list(self, columns=None, filters=None, limit=None,
                          marker=None, sort_key=None, sort_dir=None):
        # list-ify columns default values because it is bad form
        # to include a mutable list in function definitions.
        if columns is None:
            columns = [models.Node.id]
        else:
            columns = [getattr(models.Node, c) for c in columns]

        query = model_query(*columns, base_model=models.Node)
        query = self._add_nodes_filters(query, filters)
        return _paginate_query(models.Node, limit, marker,
                               sort_key, sort_dir, query)

    def get_node_list(self, filters=None, limit=None, marker=None,
                      sort_key=None, sort_dir=None):
        query = model_query(models.Node)
        query = self._add_nodes_filters(query, filters)
        return _paginate_query(models.Node, limit, marker,
                               sort_key, sort_dir, query)

    def reserve_node(self, tag, node_id):
        session = get_session()
        with session.begin():
            query = model_query(models.Node, session=session)
            query = add_identity_filter(query, node_id)
            # be optimistic and assume we usually create a reservation
            count = query.filter_by(reservation=None).update(
                        {'reservation': tag}, synchronize_session=False)
            try:
                node = query.one()
                if count != 1:
                    # Nothing updated and node exists. Must already be
                    # locked.
                    raise exception.NodeLocked(node=node_id,
                                               host=node['reservation'])
                return node
            except NoResultFound:
                raise exception.NodeNotFound(node_id)

    def release_node(self, tag, node_id):
        session = get_session()
        with session.begin():
            query = model_query(models.Node, session=session)
            query = add_identity_filter(query, node_id)
            # be optimistic and assume we usually release a reservation
            count = query.filter_by(reservation=tag).update(
                        {'reservation': None}, synchronize_session=False)
            try:
                if count != 1:
                    node = query.one()
                    if node['reservation'] is None:
                        raise exception.NodeNotLocked(node=node_id)
                    else:
                        raise exception.NodeLocked(node=node_id,
                                                   host=node['reservation'])
            except NoResultFound:
                raise exception.NodeNotFound(node_id)

    def create_node(self, values):
        # ensure defaults are present for new nodes
        if not values.get('uuid'):
            values['uuid'] = utils.generate_uuid()

        node = models.Node()
        node.update(values)
        try:
            node.save()
        except db_exc.DBDuplicateEntry as exc:
            if 'instance_uuid' in exc.columns:
                raise exception.InstanceAssociated(
                    instance_uuid=values['instance_uuid'],
                    node=values['uuid'])
            raise exception.NodeAlreadyExists(uuid=values['uuid'])
        return node

    def get_node_by_id(self, node_id):
        query = model_query(models.Node).filter_by(id=node_id)
        try:
            return query.one()
        except NoResultFound:
            raise exception.NodeNotFound(node=node_id)

    def get_node_by_uuid(self, node_uuid):
        query = model_query(models.Node).filter_by(uuid=node_uuid)
        try:
            return query.one()
        except NoResultFound:
            raise exception.NodeNotFound(node=node_uuid)

    def get_node_by_instance(self, instance):
        if not utils.is_uuid_like(instance):
            raise exception.InvalidUUID(uuid=instance)

        query = (model_query(models.Node)
                 .filter_by(instance_uuid=instance))

        try:
            result = query.one()
        except NoResultFound:
            raise exception.InstanceNotFound(instance=instance)

        return result

    def destroy_node(self, node_id):
        session = get_session()
        with session.begin():
            query = model_query(models.Node, session=session)
            query = add_identity_filter(query, node_id)
            query.delete()

    def update_node(self, node_id, values):
        # NOTE(dtantsur): this can lead to very strange errors
        if 'uuid' in values:
            msg = _("Cannot overwrite UUID for an existing Node.")
            raise exception.InvalidParameterValue(err=msg)

        try:
            return self._do_update_node(node_id, values)
        except db_exc.DBDuplicateEntry:
            raise exception.InstanceAssociated(
                instance_uuid=values['instance_uuid'],
                node=node_id)

    def _do_update_node(self, node_id, values):
        session = get_session()
        with session.begin():
            query = model_query(models.Node, session=session)
            query = add_identity_filter(query, node_id)
            try:
                ref = query.with_lockmode('update').one()
            except NoResultFound:
                raise exception.NodeNotFound(node=node_id)

            # Prevent instance_uuid overwriting
            if values.get("instance_uuid") and ref.instance_uuid:
                raise exception.NodeAssociated(node=node_id,
                                instance=ref.instance_uuid)

            if 'provision_state' in values:
                values['provision_updated_at'] = timeutils.utcnow()

            ref.update(values)
        return ref

    def _add_pods_filters(self, query, filters):
        if filters is None:
            filters = []

        if 'associated' in filters:
            if filters['associated']:
                query = query.filter(models.Pod.instance_uuid is not None)
            else:
                query = query.filter(models.Pod.instance_uuid is None)
        if 'reserved' in filters:
            if filters['reserved']:
                query = query.filter(models.Pod.reservation is not None)
            else:
                query = query.filter(models.Pod.reservation is None)
        if 'maintenance' in filters:
            query = query.filter_by(maintenance=filters['maintenance'])
        if 'driver' in filters:
            query = query.filter_by(driver=filters['driver'])
        if 'provision_state' in filters:
            query = query.filter_by(provision_state=filters['provision_state'])
        if 'provisioned_before' in filters:
            limit = timeutils.utcnow() - datetime.timedelta(
                                         seconds=filters['provisioned_before'])
            query = query.filter(models.Pod.provision_updated_at < limit)

        return query

    def get_podinfo_list(self, columns=None, filters=None, limit=None,
                          marker=None, sort_key=None, sort_dir=None):
        # list-ify columns default values because it is bad form
        # to include a mutable list in function definitions.
        if columns is None:
            columns = [models.Pod.id]
        else:
            columns = [getattr(models.Pod, c) for c in columns]

        query = model_query(*columns, base_model=models.Pod)
        query = self._add_pods_filters(query, filters)
        return _paginate_query(models.Pod, limit, marker,
                               sort_key, sort_dir, query)

    def get_pod_list(self, filters=None, limit=None, marker=None,
                      sort_key=None, sort_dir=None):
        query = model_query(models.Pod)
        query = self._add_pods_filters(query, filters)
        return _paginate_query(models.Pod, limit, marker,
                               sort_key, sort_dir, query)

    def reserve_pod(self, tag, pod_id):
        session = get_session()
        with session.begin():
            query = model_query(models.Pod, session=session)
            query = add_identity_filter(query, pod_id)
            # be optimistic and assume we usually create a reservation
            count = query.filter_by(reservation=None).update(
                        {'reservation': tag}, synchronize_session=False)
            try:
                pod = query.one()
                if count != 1:
                    # Nothing updated and pod exists. Must already be
                    # locked.
                    raise exception.PodLocked(pod=pod_id,
                                               host=pod['reservation'])
                return pod
            except NoResultFound:
                raise exception.PodNotFound(pod_id)

    def release_pod(self, tag, pod_id):
        session = get_session()
        with session.begin():
            query = model_query(models.Pod, session=session)
            query = add_identity_filter(query, pod_id)
            # be optimistic and assume we usually release a reservation
            count = query.filter_by(reservation=tag).update(
                        {'reservation': None}, synchronize_session=False)
            try:
                if count != 1:
                    pod = query.one()
                    if pod['reservation'] is None:
                        raise exception.PodNotLocked(pod=pod_id)
                    else:
                        raise exception.PodLocked(pod=pod_id,
                                                   host=pod['reservation'])
            except NoResultFound:
                raise exception.PodNotFound(pod_id)

    def create_pod(self, values):
        # ensure defaults are present for new pods
        if not values.get('uuid'):
            values['uuid'] = utils.generate_uuid()

        pod = models.Pod()
        pod.update(values)
        try:
            pod.save()
        except db_exc.DBDuplicateEntry as exc:
            if 'instance_uuid' in exc.columns:
                raise exception.InstanceAssociated(
                    instance_uuid=values['instance_uuid'],
                    pod=values['uuid'])
            raise exception.PodAlreadyExists(uuid=values['uuid'])
        return pod

    def get_pod_by_id(self, pod_id):
        query = model_query(models.Pod).filter_by(id=pod_id)
        try:
            return query.one()
        except NoResultFound:
            raise exception.PodNotFound(pod=pod_id)

    def get_pod_by_uuid(self, pod_uuid):
        query = model_query(models.Pod).filter_by(uuid=pod_uuid)
        try:
            return query.one()
        except NoResultFound:
            raise exception.PodNotFound(pod=pod_uuid)

    def get_pods_by_bay_uuid(self, bay_uuid):
        query = model_query(models.Pod).filter_by(bay_uuid=bay_uuid)
        try:
            return query.all()
        except NoResultFound:
            raise exception.BayNotFound(bay=bay_uuid)

    def get_pod_by_instance(self, instance):
        if not utils.is_uuid_like(instance):
            raise exception.InvalidUUID(uuid=instance)

        query = (model_query(models.Pod)
                 .filter_by(instance_uuid=instance))

        try:
            result = query.one()
        except NoResultFound:
            raise exception.InstanceNotFound(instance=instance)

        return result

    def destroy_pod(self, pod_id):
        session = get_session()
        with session.begin():
            query = model_query(models.Pod, session=session)
            query = add_identity_filter(query, pod_id)
            query.delete()

    def update_pod(self, pod_id, values):
        # NOTE(dtantsur): this can lead to very strange errors
        if 'uuid' in values:
            msg = _("Cannot overwrite UUID for an existing Pod.")
            raise exception.InvalidParameterValue(err=msg)

        try:
            return self._do_update_pod(pod_id, values)
        except db_exc.DBDuplicateEntry:
            raise exception.InstanceAssociated(
                instance_uuid=values['instance_uuid'],
                pod=pod_id)

    def _do_update_pod(self, pod_id, values):
        session = get_session()
        with session.begin():
            query = model_query(models.Pod, session=session)
            query = add_identity_filter(query, pod_id)
            try:
                ref = query.with_lockmode('update').one()
            except NoResultFound:
                raise exception.PodNotFound(pod=pod_id)

            # Prevent instance_uuid overwriting
            if values.get("instance_uuid") and ref.instance_uuid:
                raise exception.PodAssociated(pod=pod_id,
                                instance=ref.instance_uuid)

            if 'provision_state' in values:
                values['provision_updated_at'] = timeutils.utcnow()

            ref.update(values)
        return ref

    def _add_services_filters(self, query, filters):
        if filters is None:
            filters = []

        if 'associated' in filters:
            if filters['associated']:
                query = query.filter(models.Service.instance_uuid is not None)
            else:
                query = query.filter(models.Service.instance_uuid is None)
        if 'reserved' in filters:
            if filters['reserved']:
                query = query.filter(models.Service.reservation is not None)
            else:
                query = query.filter(models.Service.reservation is None)
        if 'maintenance' in filters:
            query = query.filter_by(maintenance=filters['maintenance'])
        if 'driver' in filters:
            query = query.filter_by(driver=filters['driver'])
        if 'provision_state' in filters:
            query = query.filter_by(provision_state=filters['provision_state'])
        if 'provisioned_before' in filters:
            limit = timeutils.utcnow() - datetime.timedelta(
                                         seconds=filters['provisioned_before'])
            query = query.filter(models.Service.provision_updated_at < limit)

        return query

    def get_serviceinfo_list(self, columns=None, filters=None, limit=None,
                          marker=None, sort_key=None, sort_dir=None):
        # list-ify columns default values because it is bad form
        # to include a mutable list in function definitions.
        if columns is None:
            columns = [models.Service.id]
        else:
            columns = [getattr(models.Service, c) for c in columns]

        query = model_query(*columns, base_model=models.Service)
        query = self._add_services_filters(query, filters)
        return _paginate_query(models.Service, limit, marker,
                               sort_key, sort_dir, query)

    def get_service_list(self, filters=None, limit=None, marker=None,
                      sort_key=None, sort_dir=None):
        query = model_query(models.Service)
        query = self._add_services_filters(query, filters)
        return _paginate_query(models.Service, limit, marker,
                               sort_key, sort_dir, query)

    def reserve_service(self, tag, service_id):
        session = get_session()
        with session.begin():
            query = model_query(models.Service, session=session)
            query = add_identity_filter(query, service_id)
            # be optimistic and assume we usually create a reservation
            count = query.filter_by(reservation=None).update(
                        {'reservation': tag}, synchronize_session=False)
            try:
                service = query.one()
                if count != 1:
                    # Nothing updated and service exists. Must already be
                    # locked.
                    raise exception.ServiceLocked(service=service_id,
                                               host=service['reservation'])
                return service
            except NoResultFound:
                raise exception.ServiceNotFound(service_id)

    def release_service(self, tag, service_id):
        session = get_session()
        with session.begin():
            query = model_query(models.Service, session=session)
            query = add_identity_filter(query, service_id)
            # be optimistic and assume we usually release a reservation
            count = query.filter_by(reservation=tag).update(
                        {'reservation': None}, synchronize_session=False)
            try:
                if count != 1:
                    service = query.one()
                    if service['reservation'] is None:
                        raise exception.ServiceNotLocked(service=service_id)
                    else:
                        raise exception.ServiceLocked(service=service_id,
                                                   host=service['reservation'])
            except NoResultFound:
                raise exception.ServiceNotFound(service_id)

    def create_service(self, values):
        # ensure defaults are present for new services
        if not values.get('uuid'):
            values['uuid'] = utils.generate_uuid()

        service = models.Service()
        service.update(values)
        try:
            service.save()
        except db_exc.DBDuplicateEntry as exc:
            if 'instance_uuid' in exc.columns:
                raise exception.InstanceAssociated(
                    instance_uuid=values['instance_uuid'],
                    service=values['uuid'])
            raise exception.ServiceAlreadyExists(uuid=values['uuid'])
        return service

    def get_service_by_id(self, service_id):
        query = model_query(models.Service).filter_by(id=service_id)
        try:
            return query.one()
        except NoResultFound:
            raise exception.ServiceNotFound(service=service_id)

    def get_service_by_uuid(self, service_uuid):
        query = model_query(models.Service).filter_by(uuid=service_uuid)
        try:
            return query.one()
        except NoResultFound:
            raise exception.ServiceNotFound(service=service_uuid)

    def get_service_by_instance(self, instance):
        if not utils.is_uuid_like(instance):
            raise exception.InvalidUUID(uuid=instance)

        query = (model_query(models.Service)
                 .filter_by(instance_uuid=instance))

        try:
            result = query.one()
        except NoResultFound:
            raise exception.InstanceNotFound(instance=instance)

        return result

    def destroy_service(self, service_id):
        session = get_session()
        with session.begin():
            query = model_query(models.Service, session=session)
            query = add_identity_filter(query, service_id)
            query.delete()

    def update_service(self, service_id, values):
        # NOTE(dtantsur): this can lead to very strange errors
        if 'uuid' in values:
            msg = _("Cannot overwrite UUID for an existing Service.")
            raise exception.InvalidParameterValue(err=msg)

        try:
            return self._do_update_service(service_id, values)
        except db_exc.DBDuplicateEntry:
            raise exception.InstanceAssociated(
                instance_uuid=values['instance_uuid'],
                service=service_id)

    def _do_update_service(self, service_id, values):
        session = get_session()
        with session.begin():
            query = model_query(models.Service, session=session)
            query = add_identity_filter(query, service_id)
            try:
                ref = query.with_lockmode('update').one()
            except NoResultFound:
                raise exception.ServiceNotFound(service=service_id)

            # Prevent instance_uuid overwriting
            if values.get("instance_uuid") and ref.instance_uuid:
                raise exception.ServiceAssociated(service=service_id,
                                instance=ref.instance_uuid)

            if 'provision_state' in values:
                values['provision_updated_at'] = timeutils.utcnow()

            ref.update(values)
        return ref
