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

from oslo_db import exception as db_exc
from oslo_db.sqlalchemy import session as db_session
from oslo_db.sqlalchemy import utils as db_utils
from oslo_log import log
from oslo_utils import importutils
from oslo_utils import strutils
from oslo_utils import timeutils
from oslo_utils import uuidutils
import sqlalchemy as sa
from sqlalchemy.orm.exc import MultipleResultsFound
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.sql import func

from magnum.common import clients
from magnum.common import context as request_context
from magnum.common import exception
import magnum.conf
from magnum.db import api
from magnum.db.sqlalchemy import models
from magnum.i18n import _

profiler_sqlalchemy = importutils.try_import('osprofiler.sqlalchemy')

CONF = magnum.conf.CONF

LOG = log.getLogger(__name__)

_FACADE = None


def _create_facade_lazily():
    global _FACADE
    if _FACADE is None:
        _FACADE = db_session.EngineFacade.from_config(CONF)
        if profiler_sqlalchemy:
            if CONF.profiler.enabled and CONF.profiler.trace_sqlalchemy:
                profiler_sqlalchemy.add_tracing(sa, _FACADE.get_engine(), "db")

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
    if strutils.is_int_like(value):
        return query.filter_by(id=value)
    elif uuidutils.is_uuid_like(value):
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
    try:
        query = db_utils.paginate_query(query, model, limit, sort_keys,
                                        marker=marker, sort_dir=sort_dir)
    except db_exc.InvalidSortKey:
        raise exception.InvalidParameterValue(
            _('The sort_key value "%(key)s" is an invalid field for sorting')
            % {'key': sort_key})
    return query.all()


class Connection(api.Connection):
    """SqlAlchemy connection."""

    def __init__(self):
        pass

    def _add_tenant_filters(self, context, query):
        if context.is_admin and context.all_tenants:
            return query

        admin_context = request_context.make_admin_context(all_tenants=True)
        osc = clients.OpenStackClients(admin_context)
        kst = osc.keystone()

        # User in a regular project (not in the trustee domain)
        if context.project_id and context.domain_id != kst.trustee_domain_id:
            query = query.filter_by(project_id=context.project_id)
        # Match project ID component in trustee user's user name against
        # cluster's project_id to associate per-cluster trustee users who have
        # no project information with the project their clusters/cluster models
        # reside in. This is equivalent to the project filtering above.
        elif context.domain_id == kst.trustee_domain_id:
            user_name = kst.client.users.get(context.user_id).name
            user_project = user_name.split('_', 2)[1]
            query = query.filter_by(project_id=user_project)
        else:
            query = query.filter_by(user_id=context.user_id)

        return query

    def _add_clusters_filters(self, query, filters):
        if filters is None:
            filters = {}

        possible_filters = ["cluster_template_id", "name", "stack_id",
                            "api_address", "node_addresses", "project_id",
                            "user_id"]

        filter_names = set(filters).intersection(possible_filters)
        filter_dict = {filter_name: filters[filter_name]
                       for filter_name in filter_names}

        query = query.filter_by(**filter_dict)

        if 'status' in filters:
            query = query.filter(models.Cluster.status.in_(filters['status']))

        # Helper to filter based on node_count field from nodegroups
        def filter_node_count(query, node_count, is_master=False):
            nfunc = func.sum(models.NodeGroup.node_count)
            nquery = model_query(models.NodeGroup)
            if is_master:
                nquery = nquery.filter(models.NodeGroup.role == 'master')
            else:
                nquery = nquery.filter(models.NodeGroup.role != 'master')
            nquery = nquery.group_by(models.NodeGroup.cluster_id)
            nquery = nquery.having(nfunc == node_count)
            uuids = [ng.cluster_id for ng in nquery.all()]
            return query.filter(models.Cluster.uuid.in_(uuids))

        if 'node_count' in filters:
            query = filter_node_count(
                query, filters['node_count'], is_master=False)
        if 'master_count' in filters:
            query = filter_node_count(
                query, filters['master_count'], is_master=True)

        return query

    def get_cluster_list(self, context, filters=None, limit=None, marker=None,
                         sort_key=None, sort_dir=None):
        query = model_query(models.Cluster)
        query = self._add_tenant_filters(context, query)
        query = self._add_clusters_filters(query, filters)
        return _paginate_query(models.Cluster, limit, marker,
                               sort_key, sort_dir, query)

    def create_cluster(self, values):
        # ensure defaults are present for new clusters
        if not values.get('uuid'):
            values['uuid'] = uuidutils.generate_uuid()

        cluster = models.Cluster()
        cluster.update(values)
        try:
            cluster.save()
        except db_exc.DBDuplicateEntry:
            raise exception.ClusterAlreadyExists(uuid=values['uuid'])
        return cluster

    def get_cluster_by_id(self, context, cluster_id):
        query = model_query(models.Cluster)
        query = self._add_tenant_filters(context, query)
        query = query.filter_by(id=cluster_id)
        try:
            return query.one()
        except NoResultFound:
            raise exception.ClusterNotFound(cluster=cluster_id)

    def get_cluster_by_name(self, context, cluster_name):
        query = model_query(models.Cluster)
        query = self._add_tenant_filters(context, query)
        query = query.filter_by(name=cluster_name)
        try:
            return query.one()
        except MultipleResultsFound:
            raise exception.Conflict('Multiple clusters exist with same name.'
                                     ' Please use the cluster uuid instead.')
        except NoResultFound:
            raise exception.ClusterNotFound(cluster=cluster_name)

    def get_cluster_by_uuid(self, context, cluster_uuid):
        query = model_query(models.Cluster)
        query = self._add_tenant_filters(context, query)
        query = query.filter_by(uuid=cluster_uuid)
        try:
            return query.one()
        except NoResultFound:
            raise exception.ClusterNotFound(cluster=cluster_uuid)

    def get_cluster_stats(self, context, project_id=None):
        query = model_query(models.Cluster)
        node_count_col = models.NodeGroup.node_count
        ncfunc = func.sum(node_count_col)

        if project_id:
            query = query.filter_by(project_id=project_id)
            nquery = query.session.query(ncfunc.label("nodes")).filter_by(
                project_id=project_id)
        else:
            nquery = query.session.query(ncfunc.label("nodes"))

        clusters = query.count()
        nodes = int(nquery.one()[0]) if nquery.one()[0] else 0
        return clusters, nodes

    def get_cluster_count_all(self, context, filters=None):
        query = model_query(models.Cluster)
        query = self._add_tenant_filters(context, query)
        query = self._add_clusters_filters(query, filters)
        return query.count()

    def destroy_cluster(self, cluster_id):
        session = get_session()
        with session.begin():
            query = model_query(models.Cluster, session=session)
            query = add_identity_filter(query, cluster_id)

            try:
                query.one()
            except NoResultFound:
                raise exception.ClusterNotFound(cluster=cluster_id)

            query.delete()

    def update_cluster(self, cluster_id, values):
        # NOTE(dtantsur): this can lead to very strange errors
        if 'uuid' in values:
            msg = _("Cannot overwrite UUID for an existing Cluster.")
            raise exception.InvalidParameterValue(err=msg)

        return self._do_update_cluster(cluster_id, values)

    def _do_update_cluster(self, cluster_id, values):
        session = get_session()
        with session.begin():
            query = model_query(models.Cluster, session=session)
            query = add_identity_filter(query, cluster_id)
            try:
                ref = query.with_for_update().one()
            except NoResultFound:
                raise exception.ClusterNotFound(cluster=cluster_id)

            ref.update(values)
        return ref

    def _add_cluster_template_filters(self, query, filters):
        if filters is None:
            filters = {}

        possible_filters = ["name", "image_id", "flavor_id",
                            "master_flavor_id", "keypair_id",
                            "external_network_id", "dns_nameserver",
                            "project_id", "user_id", "labels"]

        filter_names = set(filters).intersection(possible_filters)
        filter_dict = {filter_name: filters[filter_name]
                       for filter_name in filter_names}

        return query.filter_by(**filter_dict)

    def get_cluster_template_list(self, context, filters=None, limit=None,
                                  marker=None, sort_key=None, sort_dir=None):
        query = model_query(models.ClusterTemplate)
        query = self._add_tenant_filters(context, query)
        query = self._add_cluster_template_filters(query, filters)
        # include public (and not hidden)  ClusterTemplates
        public_q = model_query(models.ClusterTemplate).filter_by(
            public=True, hidden=False)
        query = query.union(public_q)
        # include hidden and public ClusterTemplate if admin
        if context.is_admin:
            hidden_q = model_query(models.ClusterTemplate).filter_by(
                public=True, hidden=True)
            query = query.union(hidden_q)

        return _paginate_query(models.ClusterTemplate, limit, marker,
                               sort_key, sort_dir, query)

    def create_cluster_template(self, values):
        # ensure defaults are present for new ClusterTemplates
        if not values.get('uuid'):
            values['uuid'] = uuidutils.generate_uuid()

        cluster_template = models.ClusterTemplate()
        cluster_template.update(values)
        try:
            cluster_template.save()
        except db_exc.DBDuplicateEntry:
            raise exception.ClusterTemplateAlreadyExists(uuid=values['uuid'])
        return cluster_template

    def get_cluster_template_by_id(self, context, cluster_template_id):
        query = model_query(models.ClusterTemplate)
        query = self._add_tenant_filters(context, query)
        public_q = model_query(models.ClusterTemplate).filter_by(public=True)
        query = query.union(public_q)
        query = query.filter(models.ClusterTemplate.id == cluster_template_id)
        try:
            return query.one()
        except NoResultFound:
            raise exception.ClusterTemplateNotFound(
                clustertemplate=cluster_template_id)

    def get_cluster_template_by_uuid(self, context, cluster_template_uuid):
        query = model_query(models.ClusterTemplate)
        query = self._add_tenant_filters(context, query)
        public_q = model_query(models.ClusterTemplate).filter_by(public=True)
        query = query.union(public_q)
        query = query.filter(
                models.ClusterTemplate.uuid == cluster_template_uuid)
        try:
            return query.one()
        except NoResultFound:
            raise exception.ClusterTemplateNotFound(
                clustertemplate=cluster_template_uuid)

    def get_cluster_template_by_name(self, context, cluster_template_name):
        query = model_query(models.ClusterTemplate)
        query = self._add_tenant_filters(context, query)
        public_q = model_query(models.ClusterTemplate).filter_by(public=True)
        query = query.union(public_q)
        query = query.filter(
                models.ClusterTemplate.name == cluster_template_name)
        try:
            return query.one()
        except MultipleResultsFound:
            raise exception.Conflict('Multiple ClusterTemplates exist with'
                                     ' same name. Please use the '
                                     'ClusterTemplate uuid instead.')
        except NoResultFound:
            raise exception.ClusterTemplateNotFound(
                clustertemplate=cluster_template_name)

    def _is_cluster_template_referenced(self, session, cluster_template_uuid):
        """Checks whether the ClusterTemplate is referenced by cluster(s)."""
        query = model_query(models.Cluster, session=session)
        query = self._add_clusters_filters(query, {'cluster_template_id':
                                                   cluster_template_uuid})
        return query.count() != 0

    def _is_publishing_cluster_template(self, values):
        if (len(values) == 1 and (
                ('public' in values and values['public'] is True) or
                ('hidden' in values) or
                ('tags' in values and values['tags'] is not None))):
            return True
        return False

    def destroy_cluster_template(self, cluster_template_id):
        session = get_session()
        with session.begin():
            query = model_query(models.ClusterTemplate, session=session)
            query = add_identity_filter(query, cluster_template_id)

            try:
                cluster_template_ref = query.one()
            except NoResultFound:
                raise exception.ClusterTemplateNotFound(
                    clustertemplate=cluster_template_id)

            if self._is_cluster_template_referenced(
                    session, cluster_template_ref['uuid']):
                raise exception.ClusterTemplateReferenced(
                    clustertemplate=cluster_template_id)

            query.delete()

    def update_cluster_template(self, cluster_template_id, values):
        # NOTE(dtantsur): this can lead to very strange errors
        if 'uuid' in values:
            msg = _("Cannot overwrite UUID for an existing ClusterTemplate.")
            raise exception.InvalidParameterValue(err=msg)

        return self._do_update_cluster_template(cluster_template_id, values)

    def _do_update_cluster_template(self, cluster_template_id, values):
        session = get_session()
        with session.begin():
            query = model_query(models.ClusterTemplate, session=session)
            query = add_identity_filter(query, cluster_template_id)
            try:
                ref = query.with_for_update().one()
            except NoResultFound:
                raise exception.ClusterTemplateNotFound(
                    clustertemplate=cluster_template_id)

            if self._is_cluster_template_referenced(session, ref['uuid']):
                # NOTE(flwang): We only allow to update ClusterTemplate to be
                # public, hidden and rename
                if (not self._is_publishing_cluster_template(values) and
                        list(values.keys()) != ["name"]):
                    raise exception.ClusterTemplateReferenced(
                        clustertemplate=cluster_template_id)

            ref.update(values)
        return ref

    def create_x509keypair(self, values):
        # ensure defaults are present for new x509keypairs
        if not values.get('uuid'):
            values['uuid'] = uuidutils.generate_uuid()

        x509keypair = models.X509KeyPair()
        x509keypair.update(values)
        try:
            x509keypair.save()
        except db_exc.DBDuplicateEntry:
            raise exception.X509KeyPairAlreadyExists(uuid=values['uuid'])
        return x509keypair

    def get_x509keypair_by_id(self, context, x509keypair_id):
        query = model_query(models.X509KeyPair)
        query = self._add_tenant_filters(context, query)
        query = query.filter_by(id=x509keypair_id)
        try:
            return query.one()
        except NoResultFound:
            raise exception.X509KeyPairNotFound(x509keypair=x509keypair_id)

    def get_x509keypair_by_uuid(self, context, x509keypair_uuid):
        query = model_query(models.X509KeyPair)
        query = self._add_tenant_filters(context, query)
        query = query.filter_by(uuid=x509keypair_uuid)
        try:
            return query.one()
        except NoResultFound:
            raise exception.X509KeyPairNotFound(x509keypair=x509keypair_uuid)

    def destroy_x509keypair(self, x509keypair_id):
        session = get_session()
        with session.begin():
            query = model_query(models.X509KeyPair, session=session)
            query = add_identity_filter(query, x509keypair_id)
            count = query.delete()
            if count != 1:
                raise exception.X509KeyPairNotFound(x509keypair_id)

    def update_x509keypair(self, x509keypair_id, values):
        # NOTE(dtantsur): this can lead to very strange errors
        if 'uuid' in values:
            msg = _("Cannot overwrite UUID for an existing X509KeyPair.")
            raise exception.InvalidParameterValue(err=msg)

        return self._do_update_x509keypair(x509keypair_id, values)

    def _do_update_x509keypair(self, x509keypair_id, values):
        session = get_session()
        with session.begin():
            query = model_query(models.X509KeyPair, session=session)
            query = add_identity_filter(query, x509keypair_id)
            try:
                ref = query.with_for_update().one()
            except NoResultFound:
                raise exception.X509KeyPairNotFound(x509keypair=x509keypair_id)

            ref.update(values)
        return ref

    def _add_x509keypairs_filters(self, query, filters):
        if filters is None:
            filters = {}

        if 'project_id' in filters:
            query = query.filter_by(project_id=filters['project_id'])
        if 'user_id' in filters:
            query = query.filter_by(user_id=filters['user_id'])

        return query

    def get_x509keypair_list(self, context, filters=None, limit=None,
                             marker=None, sort_key=None, sort_dir=None):
        query = model_query(models.X509KeyPair)
        query = self._add_tenant_filters(context, query)
        query = self._add_x509keypairs_filters(query, filters)
        return _paginate_query(models.X509KeyPair, limit, marker,
                               sort_key, sort_dir, query)

    def destroy_magnum_service(self, magnum_service_id):
        session = get_session()
        with session.begin():
            query = model_query(models.MagnumService, session=session)
            query = add_identity_filter(query, magnum_service_id)
            count = query.delete()
            if count != 1:
                raise exception.MagnumServiceNotFound(
                    magnum_service_id=magnum_service_id)

    def update_magnum_service(self, magnum_service_id, values):
        session = get_session()
        with session.begin():
            query = model_query(models.MagnumService, session=session)
            query = add_identity_filter(query, magnum_service_id)
            try:
                ref = query.with_for_update().one()
            except NoResultFound:
                raise exception.MagnumServiceNotFound(
                    magnum_service_id=magnum_service_id)

            if 'report_count' in values:
                if values['report_count'] > ref.report_count:
                    ref.last_seen_up = timeutils.utcnow()

            ref.update(values)
        return ref

    def get_magnum_service_by_host_and_binary(self, host, binary):
        query = model_query(models.MagnumService)
        query = query.filter_by(host=host, binary=binary)
        try:
            return query.one()
        except NoResultFound:
            return None

    def create_magnum_service(self, values):
        magnum_service = models.MagnumService()
        magnum_service.update(values)
        try:
            magnum_service.save()
        except db_exc.DBDuplicateEntry:
            host = values["host"]
            binary = values["binary"]
            LOG.warning("Magnum service with same host:%(host)s and"
                        " binary:%(binary)s had been saved into DB",
                        {'host': host, 'binary': binary})
            query = model_query(models.MagnumService)
            query = query.filter_by(host=host, binary=binary)
            return query.one()
        return magnum_service

    def get_magnum_service_list(self, disabled=None, limit=None,
                                marker=None, sort_key=None, sort_dir=None
                                ):
        query = model_query(models.MagnumService)
        if disabled:
            query = query.filter_by(disabled=disabled)

        return _paginate_query(models.MagnumService, limit, marker,
                               sort_key, sort_dir, query)

    def create_quota(self, values):
        quotas = models.Quota()
        quotas.update(values)
        try:
            quotas.save()
        except db_exc.DBDuplicateEntry:
            raise exception.QuotaAlreadyExists(project_id=values['project_id'],
                                               resource=values['resource'])
        return quotas

    def _add_quota_filters(self, query, filters):
        if filters is None:
            filters = {}

        possible_filters = ["resource", "project_id"]

        filter_names = set(filters).intersection(possible_filters)
        filter_dict = {filter_name: filters[filter_name]
                       for filter_name in filter_names}

        query = query.filter_by(**filter_dict)
        return query

    def get_quota_list(self, context, filters=None, limit=None, marker=None,
                       sort_key=None, sort_dir=None):
        query = model_query(models.Quota)
        query = self._add_quota_filters(query, filters)
        return _paginate_query(models.Quota, limit, marker,
                               sort_key, sort_dir, query)

    def update_quota(self, project_id, values):
        session = get_session()
        with session.begin():
            query = model_query(models.Quota, session=session)
            resource = values['resource']
            try:
                query = query.filter_by(project_id=project_id).filter_by(
                    resource=resource)
                ref = query.with_for_update().one()
            except NoResultFound:
                msg = (_('project_id %(project_id)s resource %(resource)s.') %
                       {'project_id': project_id, 'resource': resource})
                raise exception.QuotaNotFound(msg=msg)

            ref.update(values)
        return ref

    def delete_quota(self, project_id, resource):
        session = get_session()
        with session.begin():
            query = model_query(models.Quota, session=session) \
                .filter_by(project_id=project_id) \
                .filter_by(resource=resource)

            try:
                query.one()
            except NoResultFound:
                msg = (_('project_id %(project_id)s resource %(resource)s.') %
                       {'project_id': project_id, 'resource': resource})
                raise exception.QuotaNotFound(msg=msg)

            query.delete()

    def get_quota_by_id(self, context, quota_id):
        query = model_query(models.Quota)
        query = query.filter_by(id=quota_id)
        try:
            return query.one()
        except NoResultFound:
            msg = _('quota id %s .') % quota_id
            raise exception.QuotaNotFound(msg=msg)

    def quota_get_all_by_project_id(self, project_id):
        query = model_query(models.Quota)
        result = query.filter_by(project_id=project_id).all()

        return result

    def get_quota_by_project_id_resource(self, project_id, resource):
        query = model_query(models.Quota)
        query = query.filter_by(project_id=project_id).filter_by(
            resource=resource)

        try:
            return query.one()
        except NoResultFound:
            msg = (_('project_id %(project_id)s resource %(resource)s.') %
                   {'project_id': project_id, 'resource': resource})
            raise exception.QuotaNotFound(msg=msg)

    def _add_federation_filters(self, query, filters):
        if filters is None:
            filters = {}

        possible_filters = ["name", "project_id", "hostcluster_id",
                            "member_ids", "properties"]

        # TODO(clenimar): implement 'member_ids' filter as a contains query,
        # so we return all the federations that have the given clusters,
        # instead of all the federations that *only* have the exact given
        # clusters.

        filter_names = set(filters).intersection(possible_filters)
        filter_dict = {filter_name: filters[filter_name]
                       for filter_name in filter_names}

        query = query.filter_by(**filter_dict)

        if 'status' in filters:
            query = query.filter(
                models.Federation.status.in_(filters['status']))

        return query

    def get_federation_by_id(self, context, federation_id):
        query = model_query(models.Federation)
        query = self._add_tenant_filters(context, query)
        query = query.filter_by(id=federation_id)
        try:
            return query.one()
        except NoResultFound:
            raise exception.FederationNotFound(federation=federation_id)

    def get_federation_by_uuid(self, context, federation_uuid):
        query = model_query(models.Federation)
        query = self._add_tenant_filters(context, query)
        query = query.filter_by(uuid=federation_uuid)
        try:
            return query.one()
        except NoResultFound:
            raise exception.FederationNotFound(federation=federation_uuid)

    def get_federation_by_name(self, context, federation_name):
        query = model_query(models.Federation)
        query = self._add_tenant_filters(context, query)
        query = query.filter_by(name=federation_name)
        try:
            return query.one()
        except MultipleResultsFound:
            raise exception.Conflict('Multiple federations exist with same '
                                     'name. Please use the federation uuid '
                                     'instead.')
        except NoResultFound:
            raise exception.FederationNotFound(federation=federation_name)

    def get_federation_list(self, context, limit=None, marker=None,
                            sort_key=None, sort_dir=None, filters=None):
        query = model_query(models.Federation)
        query = self._add_tenant_filters(context, query)
        query = self._add_federation_filters(query, filters)
        return _paginate_query(models.Federation, limit, marker,
                               sort_key, sort_dir, query)

    def create_federation(self, values):
        if not values.get('uuid'):
            values['uuid'] = uuidutils.generate_uuid()

        federation = models.Federation()
        federation.update(values)
        try:
            federation.save()
        except db_exc.DBDuplicateEntry:
            raise exception.FederationAlreadyExists(uuid=values['uuid'])
        return federation

    def destroy_federation(self, federation_id):
        session = get_session()
        with session.begin():
            query = model_query(models.Federation, session=session)
            query = add_identity_filter(query, federation_id)

            try:
                query.one()
            except NoResultFound:
                raise exception.FederationNotFound(federation=federation_id)

            query.delete()

    def update_federation(self, federation_id, values):
        if 'uuid' in values:
            msg = _("Cannot overwrite UUID for an existing Federation.")
            raise exception.InvalidParameterValue(err=msg)

        return self._do_update_federation(federation_id, values)

    def _do_update_federation(self, federation_id, values):
        session = get_session()
        with session.begin():
            query = model_query(models.Federation, session=session)
            query = add_identity_filter(query, federation_id)
            try:
                ref = query.with_for_update().one()
            except NoResultFound:
                raise exception.FederationNotFound(federation=federation_id)

            ref.update(values)

        return ref

    def _add_nodegoup_filters(self, query, filters):
        if filters is None:
            filters = {}

        possible_filters = ["name", "node_count", "node_addresses",
                            "role", "is_default"]

        filter_names = set(filters).intersection(possible_filters)
        filter_dict = {filter_name: filters[filter_name]
                       for filter_name in filter_names}

        query = query.filter_by(**filter_dict)

        if 'status' in filters:
            query = query.filter(
                models.NodeGroup.status.in_(filters['status']))

        return query

    def create_nodegroup(self, values):
        if not values.get('uuid'):
            values['uuid'] = uuidutils.generate_uuid()

        nodegroup = models.NodeGroup()
        nodegroup.update(values)
        try:
            nodegroup.save()
        except db_exc.DBDuplicateEntry:
            raise exception.NodeGroupAlreadyExists(
                cluster_id=values['cluster_id'], name=values['name'])
        return nodegroup

    def destroy_nodegroup(self, cluster_id, nodegroup_id):
        session = get_session()
        with session.begin():
            query = model_query(models.NodeGroup, session=session)
            query = add_identity_filter(query, nodegroup_id)
            query = query.filter_by(cluster_id=cluster_id)
            try:
                query.one()
            except NoResultFound:
                raise exception.NodeGroupNotFound(nodegroup=nodegroup_id)
            query.delete()

    def update_nodegroup(self, cluster_id, nodegroup_id, values):
        return self._do_update_nodegroup(cluster_id, nodegroup_id, values)

    def _do_update_nodegroup(self, cluster_id, nodegroup_id, values):
        session = get_session()
        with session.begin():
            query = model_query(models.NodeGroup, session=session)
            query = add_identity_filter(query, nodegroup_id)
            query = query.filter_by(cluster_id=cluster_id)
            try:
                ref = query.with_for_update().one()
            except NoResultFound:
                raise exception.NodeGroupNotFound(nodegroup=nodegroup_id)

            ref.update(values)
        return ref

    def get_nodegroup_by_id(self, context, cluster_id, nodegroup_id):
        query = model_query(models.NodeGroup)
        if not context.is_admin:
            query = query.filter_by(project_id=context.project_id)
        query = query.filter_by(cluster_id=cluster_id)
        query = query.filter_by(id=nodegroup_id)
        try:
            return query.one()
        except NoResultFound:
            raise exception.NodeGroupNotFound(nodegroup=nodegroup_id)

    def get_nodegroup_by_uuid(self, context, cluster_id, nodegroup_uuid):
        query = model_query(models.NodeGroup)
        if not context.is_admin:
            query = query.filter_by(project_id=context.project_id)
        query = query.filter_by(cluster_id=cluster_id)
        query = query.filter_by(uuid=nodegroup_uuid)
        try:
            return query.one()
        except NoResultFound:
            raise exception.NodeGroupNotFound(nodegroup=nodegroup_uuid)

    def get_nodegroup_by_name(self, context, cluster_id, nodegroup_name):
        query = model_query(models.NodeGroup)
        if not context.is_admin:
            query = query.filter_by(project_id=context.project_id)
        query = query.filter_by(cluster_id=cluster_id)
        query = query.filter_by(name=nodegroup_name)
        try:
            return query.one()
        except MultipleResultsFound:
            raise exception.Conflict('Multiple nodegroups exist with same '
                                     'name. Please use the nodegroup uuid '
                                     'instead.')
        except NoResultFound:
            raise exception.NodeGroupNotFound(nodegroup=nodegroup_name)

    def list_cluster_nodegroups(self, context, cluster_id, filters=None,
                                limit=None, marker=None, sort_key=None,
                                sort_dir=None):
        query = model_query(models.NodeGroup)
        if not context.is_admin:
            query = query.filter_by(project_id=context.project_id)
        query = query.filter_by(cluster_id=cluster_id)
        query = self._add_nodegoup_filters(query, filters)
        return _paginate_query(models.NodeGroup, limit, marker,
                               sort_key, sort_dir, query)

    def get_cluster_nodegroup_count(self, context, cluster_id):
        query = model_query(models.NodeGroup)
        if not context.is_admin:
            query = query.filter_by(project_id=context.project_id)
        query = query.filter_by(cluster_id=cluster_id)
        return query.count()
