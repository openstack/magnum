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

from oslo_config import cfg
from oslo_db import exception as db_exc
from oslo_db.sqlalchemy import session as db_session
from oslo_db.sqlalchemy import utils as db_utils
from oslo_log import log
from oslo_utils import timeutils
from sqlalchemy.orm.exc import MultipleResultsFound
from sqlalchemy.orm.exc import NoResultFound

from magnum.common import exception
from magnum.common import utils
from magnum.db import api
from magnum.db.sqlalchemy import models
from magnum.i18n import _

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

    def _add_tenant_filters(self, context, query, opts=None):
        if opts is None:
            opts = {}

        all_tenants = opts.get('get_all_tenants', False)

        if context.is_admin and all_tenants:
            return query

        if context.project_id:
            query = query.filter_by(project_id=context.project_id)
        else:
            query = query.filter_by(user_id=context.user_id)

        return query

    def _add_bays_filters(self, query, filters):
        if filters is None:
            filters = []

        if 'baymodel_id' in filters:
            query = query.filter_by(baymodel_id=filters['baymodel_id'])
        if 'name' in filters:
            query = query.filter_by(name=filters['name'])
        if 'node_count' in filters:
            query = query.filter_by(node_count=filters['node_count'])
        if 'stack_id' in filters:
            query = query.filter_by(stack_id=filters['stack_id'])
        if 'api_address' in filters:
            query = query.filter_by(api_address=filters['api_address'])
        if 'node_addresses' in filters:
            query = query.filter_by(node_addresses=filters['node_addresses'])
        if 'project_id' in filters:
            query = query.filter_by(project_id=filters['project_id'])
        if 'user_id' in filters:
            query = query.filter_by(user_id=filters['user_id'])
        if 'status' in filters:
            query = query.filter(models.Bay.status.in_(filters['status']))

        return query

    def get_bay_list(self, context, filters=None, limit=None, marker=None,
                     sort_key=None, sort_dir=None, opts=None):
        if opts is None:
            opts = {}
        query = model_query(models.Bay)
        query = self._add_tenant_filters(context, query, opts=opts)
        query = self._add_bays_filters(query, filters)
        return _paginate_query(models.Bay, limit, marker,
                               sort_key, sort_dir, query)

    def create_bay(self, values):
        # ensure defaults are present for new bays
        if not values.get('uuid'):
            values['uuid'] = utils.generate_uuid()

        bay = models.Bay()
        bay.update(values)
        try:
            bay.save()
        except db_exc.DBDuplicateEntry:
            raise exception.BayAlreadyExists(uuid=values['uuid'])
        return bay

    def get_bay_by_id(self, context, bay_id):
        query = model_query(models.Bay)
        query = self._add_tenant_filters(context, query)
        query = query.filter_by(id=bay_id)
        try:
            return query.one()
        except NoResultFound:
            raise exception.BayNotFound(bay=bay_id)

    def get_bay_by_name(self, context, bay_name):
        query = model_query(models.Bay)
        query = self._add_tenant_filters(context, query)
        query = query.filter_by(name=bay_name)
        try:
            return query.one()
        except MultipleResultsFound:
            raise exception.Conflict('Multiple bays exist with same name.'
                                     ' Please use the bay uuid instead.')
        except NoResultFound:
            raise exception.BayNotFound(bay=bay_name)

    def get_bay_by_uuid(self, context, bay_uuid):
        query = model_query(models.Bay)
        query = self._add_tenant_filters(context, query)
        query = query.filter_by(uuid=bay_uuid)
        try:
            return query.one()
        except NoResultFound:
            raise exception.BayNotFound(bay=bay_uuid)

    def destroy_bay(self, bay_id):
        def destroy_bay_resources(session, bay_uuid):
            """Checks whether the bay does not have resources."""
            query = model_query(models.Pod, session=session)
            query = self._add_pods_filters(query, {'bay_uuid': bay_uuid})
            if query.count() != 0:
                query.delete()

            query = model_query(models.Service, session=session)
            query = self._add_services_filters(query, {'bay_uuid': bay_uuid})
            if query.count() != 0:
                query.delete()

            query = model_query(models.ReplicationController, session=session)
            query = self._add_rcs_filters(query, {'bay_uuid': bay_uuid})
            if query.count() != 0:
                query.delete()

            query = model_query(models.Container, session=session)
            query = self._add_containers_filters(query, {'bay_uuid': bay_uuid})
            if query.count() != 0:
                query.delete()

        session = get_session()
        with session.begin():
            query = model_query(models.Bay, session=session)
            query = add_identity_filter(query, bay_id)

            try:
                bay_ref = query.one()
            except NoResultFound:
                raise exception.BayNotFound(bay=bay_id)

            destroy_bay_resources(session, bay_ref['uuid'])
            query.delete()

    def update_bay(self, bay_id, values):
        # NOTE(dtantsur): this can lead to very strange errors
        if 'uuid' in values:
            msg = _("Cannot overwrite UUID for an existing Bay.")
            raise exception.InvalidParameterValue(err=msg)

        return self._do_update_bay(bay_id, values)

    def _do_update_bay(self, bay_id, values):
        session = get_session()
        with session.begin():
            query = model_query(models.Bay, session=session)
            query = add_identity_filter(query, bay_id)
            try:
                ref = query.with_lockmode('update').one()
            except NoResultFound:
                raise exception.BayNotFound(bay=bay_id)

            if 'provision_state' in values:
                values['provision_updated_at'] = timeutils.utcnow()

            ref.update(values)
        return ref

    def create_bay_lock(self, bay_uuid, conductor_id):
        session = get_session()
        with session.begin():
            query = model_query(models.BayLock, session=session)
            lock = query.filter_by(bay_uuid=bay_uuid).first()
            if lock is not None:
                return lock.conductor_id
            session.add(models.BayLock(bay_uuid=bay_uuid,
                                       conductor_id=conductor_id))

    def steal_bay_lock(self, bay_uuid, old_conductor_id, new_conductor_id):
        session = get_session()
        with session.begin():
            query = model_query(models.BayLock, session=session)
            lock = query.filter_by(bay_uuid=bay_uuid).first()
            if lock is None:
                return True
            elif lock.conductor_id != old_conductor_id:
                return lock.conductor_id
            else:
                lock.update({'conductor_id': new_conductor_id})

    def release_bay_lock(self, bay_uuid, conductor_id):
        session = get_session()
        with session.begin():
            query = model_query(models.BayLock, session=session)
            query = query.filter_by(bay_uuid=bay_uuid,
                                    conductor_id=conductor_id)
            count = query.delete()
            if count == 0:
                return True

    def _add_baymodels_filters(self, query, filters):
        if filters is None:
            filters = []

        if 'name' in filters:
            query = query.filter_by(name=filters['name'])
        if 'image_id' in filters:
            query = query.filter_by(image_id=filters['image_id'])
        if 'flavor_id' in filters:
            query = query.filter_by(flavor_id=filters['flavor_id'])
        if 'master_flavor_id' in filters:
            query = query.filter_by(
                master_flavor_id=filters['master_flavor_id'])
        if 'keypair_id' in filters:
            query = query.filter_by(keypair_id=filters['keypair_id'])
        if 'external_network_id' in filters:
            query = query.filter_by(
                external_network_id=filters['external_network_id'])
        if 'dns_nameserver' in filters:
            query = query.filter_by(dns_nameserver=filters['dns_nameserver'])
        if 'project_id' in filters:
            query = query.filter_by(project_id=filters['project_id'])
        if 'user_id' in filters:
            query = query.filter_by(user_id=filters['user_id'])

        return query

    def get_baymodel_list(self, context, filters=None, limit=None, marker=None,
                          sort_key=None, sort_dir=None):
        query = model_query(models.BayModel)
        query = self._add_tenant_filters(context, query)
        query = self._add_baymodels_filters(query, filters)
        return _paginate_query(models.BayModel, limit, marker,
                               sort_key, sort_dir, query)

    def create_baymodel(self, values):
        # ensure defaults are present for new baymodels
        if not values.get('uuid'):
            values['uuid'] = utils.generate_uuid()

        baymodel = models.BayModel()
        baymodel.update(values)
        try:
            baymodel.save()
        except db_exc.DBDuplicateEntry:
            raise exception.BayModelAlreadyExists(uuid=values['uuid'])
        return baymodel

    def get_baymodel_by_id(self, context, baymodel_id):
        query = model_query(models.BayModel)
        query = self._add_tenant_filters(context, query)
        query = query.filter_by(id=baymodel_id)
        try:
            return query.one()
        except NoResultFound:
            raise exception.BayModelNotFound(baymodel=baymodel_id)

    def get_baymodel_by_uuid(self, context, baymodel_uuid):
        query = model_query(models.BayModel)
        query = self._add_tenant_filters(context, query)
        query = query.filter_by(uuid=baymodel_uuid)
        try:
            return query.one()
        except NoResultFound:
            raise exception.BayModelNotFound(baymodel=baymodel_uuid)

    def get_baymodel_by_name(self, context, baymodel_name):
        query = model_query(models.BayModel)
        query = self._add_tenant_filters(context, query)
        query = query.filter_by(name=baymodel_name)
        try:
            return query.one()
        except MultipleResultsFound:
            raise exception.Conflict('Multiple baymodels exist with same name.'
                                     ' Please use the baymodel uuid instead.')
        except NoResultFound:
            raise exception.BayModelNotFound(baymodel=baymodel_name)

    def destroy_baymodel(self, baymodel_id):
        def is_baymodel_referenced(session, baymodel_uuid):
            """Checks whether the baymodel is referenced by bay(s)."""
            query = model_query(models.Bay, session=session)
            query = self._add_bays_filters(query,
                                           {'baymodel_id': baymodel_uuid})
            return query.count() != 0

        session = get_session()
        with session.begin():
            query = model_query(models.BayModel, session=session)
            query = add_identity_filter(query, baymodel_id)

            try:
                baymodel_ref = query.one()
            except NoResultFound:
                raise exception.BayModelNotFound(baymodel=baymodel_id)

            if is_baymodel_referenced(session, baymodel_ref['uuid']):
                raise exception.BayModelReferenced(baymodel=baymodel_id)

            query.delete()

    def update_baymodel(self, baymodel_id, values):
        # NOTE(dtantsur): this can lead to very strange errors
        if 'uuid' in values:
            msg = _("Cannot overwrite UUID for an existing BayModel.")
            raise exception.InvalidParameterValue(err=msg)

        return self._do_update_baymodel(baymodel_id, values)

    def _do_update_baymodel(self, baymodel_id, values):
        session = get_session()
        with session.begin():
            query = model_query(models.BayModel, session=session)
            query = add_identity_filter(query, baymodel_id)
            try:
                ref = query.with_lockmode('update').one()
            except NoResultFound:
                raise exception.BayModelNotFound(baymodel=baymodel_id)

            ref.update(values)
        return ref

    def _add_containers_filters(self, query, filters):
        if filters is None:
            filters = []

        if 'name' in filters:
            query = query.filter_by(name=filters['name'])
        if 'image' in filters:
            query = query.filter_by(image=filters['image'])
        if 'project_id' in filters:
            query = query.filter_by(project_id=filters['project_id'])
        if 'user_id' in filters:
            query = query.filter_by(user_id=filters['user_id'])

        return query

    def get_container_list(self, context, filters=None, limit=None,
                           marker=None, sort_key=None, sort_dir=None):
        query = model_query(models.Container)
        query = self._add_tenant_filters(context, query)
        query = self._add_containers_filters(query, filters)
        return _paginate_query(models.Container, limit, marker,
                               sort_key, sort_dir, query)

    def create_container(self, values):
        # ensure defaults are present for new containers
        if not values.get('uuid'):
            values['uuid'] = utils.generate_uuid()

        container = models.Container()
        container.update(values)
        try:
            container.save()
        except db_exc.DBDuplicateEntry:
            raise exception.ContainerAlreadyExists(uuid=values['uuid'])
        return container

    def get_container_by_id(self, context, container_id):
        query = model_query(models.Container)
        query = self._add_tenant_filters(context, query)
        query = query.filter_by(id=container_id)
        try:
            return query.one()
        except NoResultFound:
            raise exception.ContainerNotFound(container=container_id)

    def get_container_by_uuid(self, context, container_uuid):
        query = model_query(models.Container)
        query = self._add_tenant_filters(context, query)
        query = query.filter_by(uuid=container_uuid)
        try:
            return query.one()
        except NoResultFound:
            raise exception.ContainerNotFound(container=container_uuid)

    def get_container_by_name(self, context, container_name):
        query = model_query(models.Container)
        query = self._add_tenant_filters(context, query)
        query = query.filter_by(name=container_name)
        try:
            return query.one()
        except NoResultFound:
            raise exception.ContainerNotFound(container=container_name)
        except MultipleResultsFound:
            raise exception.Conflict('Multiple containers exist with same '
                                     'name. Please use the container uuid '
                                     'instead.')

    def destroy_container(self, container_id):
        session = get_session()
        with session.begin():
            query = model_query(models.Container, session=session)
            query = add_identity_filter(query, container_id)
            count = query.delete()
            if count != 1:
                raise exception.ContainerNotFound(container_id)

    def update_container(self, container_id, values):
        # NOTE(dtantsur): this can lead to very strange errors
        if 'uuid' in values:
            msg = _("Cannot overwrite UUID for an existing Container.")
            raise exception.InvalidParameterValue(err=msg)

        return self._do_update_container(container_id, values)

    def _do_update_container(self, container_id, values):
        session = get_session()
        with session.begin():
            query = model_query(models.Container, session=session)
            query = add_identity_filter(query, container_id)
            try:
                ref = query.with_lockmode('update').one()
            except NoResultFound:
                raise exception.ContainerNotFound(container=container_id)

            if 'provision_state' in values:
                values['provision_updated_at'] = timeutils.utcnow()

            ref.update(values)
        return ref

    def _add_nodes_filters(self, query, filters):
        if filters is None:
            filters = []

        if 'associated' in filters:
            if filters['associated']:
                query = query.filter(models.Node.ironic_node_id != None)
            else:
                query = query.filter(models.Node.ironic_node_id == None)
        if 'type' in filters:
            query = query.filter_by(type=filters['type'])
        if 'image_id' in filters:
            query = query.filter_by(image_id=filters['image_id'])
        if 'project_id' in filters:
            query = query.filter_by(project_id=filters['project_id'])
        if 'user_id' in filters:
            query = query.filter_by(user_id=filters['user_id'])

        return query

    def get_node_list(self, context, filters=None, limit=None, marker=None,
                      sort_key=None, sort_dir=None):
        query = model_query(models.Node)
        query = self._add_tenant_filters(context, query)
        query = self._add_nodes_filters(query, filters)
        return _paginate_query(models.Node, limit, marker,
                               sort_key, sort_dir, query)

    def create_node(self, values):
        # ensure defaults are present for new nodes
        if not values.get('uuid'):
            values['uuid'] = utils.generate_uuid()

        node = models.Node()
        node.update(values)
        try:
            node.save()
        except db_exc.DBDuplicateEntry as exc:
            if 'ironic_node_id' in exc.columns:
                raise exception.InstanceAssociated(
                    instance_uuid=values['ironic_node_id'],
                    node=values['uuid'])
            raise exception.NodeAlreadyExists(uuid=values['uuid'])
        return node

    def get_node_by_id(self, context, node_id):
        query = model_query(models.Node)
        query = self._add_tenant_filters(context, query)
        query = query.filter_by(id=node_id)
        try:
            return query.one()
        except NoResultFound:
            raise exception.NodeNotFound(node=node_id)

    def get_node_by_uuid(self, context, node_uuid):
        query = model_query(models.Node)
        query = self._add_tenant_filters(context, query)
        query = query.filter_by(uuid=node_uuid)
        try:
            return query.one()
        except NoResultFound:
            raise exception.NodeNotFound(node=node_uuid)

    def destroy_node(self, node_id):
        session = get_session()
        with session.begin():
            query = model_query(models.Node, session=session)
            query = add_identity_filter(query, node_id)
            count = query.delete()
            if count != 1:
                raise exception.NodeNotFound(node_id)

    def update_node(self, node_id, values):
        # NOTE(dtantsur): this can lead to very strange errors
        if 'uuid' in values:
            msg = _("Cannot overwrite UUID for an existing Node.")
            raise exception.InvalidParameterValue(err=msg)

        try:
            return self._do_update_node(node_id, values)
        except db_exc.DBDuplicateEntry:
            raise exception.InstanceAssociated(
                instance_uuid=values['ironic_node_id'],
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

            # Prevent ironic_node_id overwriting
            if values.get("ironic_node_id") and ref.ironic_node_id:
                raise exception.NodeAssociated(
                    node=node_id,
                    instance=ref.ironic_node_id)

            ref.update(values)
        return ref

    def _add_pods_filters(self, query, filters):
        if filters is None:
            filters = []

        if 'bay_uuid' in filters:
            query = query.filter_by(bay_uuid=filters['bay_uuid'])
        if 'name' in filters:
            query = query.filter_by(name=filters['name'])
        if 'status' in filters:
            query = query.filter_by(status=filters['status'])

        return query

    def get_pod_list(self, context, filters=None, limit=None, marker=None,
                     sort_key=None, sort_dir=None):
        query = model_query(models.Pod)
        query = self._add_tenant_filters(context, query)
        query = self._add_pods_filters(query, filters)
        return _paginate_query(models.Pod, limit, marker,
                               sort_key, sort_dir, query)

    def create_pod(self, values):
        # ensure defaults are present for new pods
        if not values.get('uuid'):
            values['uuid'] = utils.generate_uuid()

        pod = models.Pod()
        pod.update(values)
        try:
            pod.save()
        except db_exc.DBDuplicateEntry:
            raise exception.PodAlreadyExists(uuid=values['uuid'])
        return pod

    def get_pod_by_id(self, context, pod_id):
        query = model_query(models.Pod)
        query = self._add_tenant_filters(context, query)
        query = query.filter_by(id=pod_id)
        try:
            return query.one()
        except NoResultFound:
            raise exception.PodNotFound(pod=pod_id)

    def get_pod_by_uuid(self, context, pod_uuid):
        query = model_query(models.Pod)
        query = self._add_tenant_filters(context, query)
        query = query.filter_by(uuid=pod_uuid)
        try:
            return query.one()
        except NoResultFound:
            raise exception.PodNotFound(pod=pod_uuid)

    def get_pod_by_name(self, pod_name):
        query = model_query(models.Pod).filter_by(name=pod_name)
        try:
            return query.one()
        except MultipleResultsFound:
            raise exception.Conflict('Multiple pods exist with same name.'
                                     ' Please use the pod uuid instead.')
        except NoResultFound:
            raise exception.PodNotFound(pod=pod_name)

    def get_pods_by_bay_uuid(self, bay_uuid):
        query = model_query(models.Pod).filter_by(bay_uuid=bay_uuid)
        try:
            return query.all()
        except NoResultFound:
            raise exception.BayNotFound(bay=bay_uuid)

    def destroy_pod(self, pod_id):
        session = get_session()
        with session.begin():
            query = model_query(models.Pod, session=session)
            query = add_identity_filter(query, pod_id)
            count = query.delete()
            if count != 1:
                raise exception.PodNotFound(pod_id)

    def update_pod(self, pod_id, values):
        # NOTE(dtantsur): this can lead to very strange errors
        if 'uuid' in values:
            msg = _("Cannot overwrite UUID for an existing Pod.")
            raise exception.InvalidParameterValue(err=msg)

        return self._do_update_pod(pod_id, values)

    def _do_update_pod(self, pod_id, values):
        session = get_session()
        with session.begin():
            query = model_query(models.Pod, session=session)
            query = add_identity_filter(query, pod_id)
            try:
                ref = query.with_lockmode('update').one()
            except NoResultFound:
                raise exception.PodNotFound(pod=pod_id)

            if 'provision_state' in values:
                values['provision_updated_at'] = timeutils.utcnow()

            ref.update(values)
        return ref

    def _add_services_filters(self, query, filters):
        if filters is None:
            filters = []

        if 'bay_uuid' in filters:
            query = query.filter_by(bay_uuid=filters['bay_uuid'])
        if 'name' in filters:
            query = query.filter_by(name=filters['name'])
        if 'ip' in filters:
            query = query.filter_by(ip=filters['ip'])
        if 'ports' in filters:
            query = query.filter_by(ports=filters['ports'])

        return query

    def get_service_list(self, context, filters=None, limit=None, marker=None,
                         sort_key=None, sort_dir=None):
        query = model_query(models.Service)
        query = self._add_tenant_filters(context, query)
        query = self._add_services_filters(query, filters)
        return _paginate_query(models.Service, limit, marker,
                               sort_key, sort_dir, query)

    def create_service(self, values):
        # ensure defaults are present for new services
        if not values.get('uuid'):
            values['uuid'] = utils.generate_uuid()

        service = models.Service()
        service.update(values)
        try:
            service.save()
        except db_exc.DBDuplicateEntry:
            raise exception.ServiceAlreadyExists(uuid=values['uuid'])
        return service

    def get_service_by_id(self, context, service_id):
        query = model_query(models.Service)
        query = self._add_tenant_filters(context, query)
        query = query.filter_by(id=service_id)
        try:
            return query.one()
        except NoResultFound:
            raise exception.ServiceNotFound(service=service_id)

    def get_service_by_uuid(self, context, service_uuid):
        query = model_query(models.Service)
        query = self._add_tenant_filters(context, query)
        query = query.filter_by(uuid=service_uuid)
        try:
            return query.one()
        except NoResultFound:
            raise exception.ServiceNotFound(service=service_uuid)

    def get_services_by_bay_uuid(self, bay_uuid):
        query = model_query(models.Service).filter_by(bay_uuid=bay_uuid)
        try:
            return query.all()
        except NoResultFound:
            raise exception.ServiceNotFound(bay=bay_uuid)

    def get_service_by_name(self, context, service_name):
        query = model_query(models.Service)
        query = self._add_tenant_filters(context, query)
        query = query.filter_by(name=service_name)
        try:
            return query.one()
        except MultipleResultsFound:
            raise exception.Conflict('Multiple services exist with same name.'
                                     ' Please use the service uuid instead.')
        except NoResultFound:
            raise exception.ServiceNotFound(service=service_name)

    def destroy_service(self, service_id):
        session = get_session()
        with session.begin():
            query = model_query(models.Service, session=session)
            query = add_identity_filter(query, service_id)
            count = query.delete()
            if count != 1:
                raise exception.ServiceNotFound(service_id)

    def update_service(self, service_id, values):
        # NOTE(dtantsur): this can lead to very strange errors
        if 'uuid' in values:
            msg = _("Cannot overwrite UUID for an existing Service.")
            raise exception.InvalidParameterValue(err=msg)

        return self._do_update_service(service_id, values)

    def _do_update_service(self, service_id, values):
        session = get_session()
        with session.begin():
            query = model_query(models.Service, session=session)
            query = add_identity_filter(query, service_id)
            try:
                ref = query.with_lockmode('update').one()
            except NoResultFound:
                raise exception.ServiceNotFound(service=service_id)

            if 'provision_state' in values:
                values['provision_updated_at'] = timeutils.utcnow()

            ref.update(values)
        return ref

    def _add_rcs_filters(self, query, filters):
        if filters is None:
            filters = []

        if 'bay_uuid' in filters:
            query = query.filter_by(bay_uuid=filters['bay_uuid'])
        if 'name' in filters:
            query = query.filter_by(name=filters['name'])
        if 'replicas' in filters:
            query = query.filter_by(replicas=filters['replicas'])

        return query

    def get_rc_list(self, context, filters=None, limit=None, marker=None,
                    sort_key=None, sort_dir=None):
        query = model_query(models.ReplicationController)
        query = self._add_tenant_filters(context, query)
        query = self._add_rcs_filters(query, filters)
        return _paginate_query(models.ReplicationController, limit, marker,
                               sort_key, sort_dir, query)

    def create_rc(self, values):
        # ensure defaults are present for new ReplicationController
        if not values.get('uuid'):
            values['uuid'] = utils.generate_uuid()

        rc = models.ReplicationController()
        rc.update(values)
        try:
            rc.save()
        except db_exc.DBDuplicateEntry:
            raise exception.ReplicationControllerAlreadyExists(
                uuid=values['uuid'])
        return rc

    def get_rc_by_id(self, context, rc_id):
        query = model_query(models.ReplicationController)
        query = self._add_tenant_filters(context, query)
        query = query.filter_by(id=rc_id)
        try:
            return query.one()
        except NoResultFound:
            raise exception.ReplicationControllerNotFound(rc=rc_id)

    def get_rc_by_uuid(self, context, rc_uuid):
        query = model_query(models.ReplicationController)
        query = self._add_tenant_filters(context, query)
        query = query.filter_by(uuid=rc_uuid)
        try:
            return query.one()
        except NoResultFound:
            raise exception.ReplicationControllerNotFound(rc=rc_uuid)

    def get_rcs_by_bay_uuid(self, bay_uuid):
        query = model_query(models.ReplicationController).filter_by(
            bay_uuid=bay_uuid)
        try:
            return query.all()
        except NoResultFound:
            raise exception.ReplicationControllerNotFound(bay=bay_uuid)

    def get_rc_by_name(self, rc_name):
        query = model_query(models.ReplicationController).filter_by(
            name=rc_name)
        try:
            return query.one()
        except MultipleResultsFound:
            raise exception.Conflict('Multiple rcs exist with same name.'
                                     ' Please use the rc uuid instead.')
        except NoResultFound:
            raise exception.ReplicationControllerNotFound(rc=rc_name)

    def destroy_rc(self, rc_id):
        session = get_session()
        with session.begin():
            query = model_query(models.ReplicationController, session=session)
            query = add_identity_filter(query, rc_id)
            count = query.delete()
            if count != 1:
                raise exception.ReplicationControllerNotFound(rc_id)

    def update_rc(self, rc_id, values):
        if 'uuid' in values:
            msg = _("Cannot overwrite UUID for an existing rc.")
            raise exception.InvalidParameterValue(err=msg)

        return self._do_update_rc(rc_id, values)

    def _do_update_rc(self, rc_id, values):
        session = get_session()
        with session.begin():
            query = model_query(models.ReplicationController, session=session)
            query = add_identity_filter(query, rc_id)
            try:
                ref = query.with_lockmode('update').one()
            except NoResultFound:
                raise exception.ReplicationControllerNotFound(rc=rc_id)

            ref.update(values)
        return ref
