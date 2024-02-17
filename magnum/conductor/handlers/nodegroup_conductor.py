# Copyright (c) 2018 European Organization for Nuclear Research.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.


import functools

from heatclient import exc
from oslo_log import log as logging

from magnum.common import exception
from magnum.common import profiler
import magnum.conf
from magnum.drivers.common import driver
from magnum.i18n import _
from magnum.objects import fields

CONF = magnum.conf.CONF

LOG = logging.getLogger(__name__)


# TODO(ttsiouts): notifications about nodegroup operations will be
#                 added in later commit.


ALLOWED_NODEGROUP_STATES = (
    fields.ClusterStatus.CREATE_COMPLETE,
    fields.ClusterStatus.UPDATE_COMPLETE,
    fields.ClusterStatus.UPDATE_IN_PROGRESS,
    fields.ClusterStatus.UPDATE_FAILED,
    fields.ClusterStatus.RESUME_COMPLETE,
    fields.ClusterStatus.RESTORE_COMPLETE,
    fields.ClusterStatus.ROLLBACK_COMPLETE,
    fields.ClusterStatus.SNAPSHOT_COMPLETE,
    fields.ClusterStatus.CHECK_COMPLETE,
    fields.ClusterStatus.ADOPT_COMPLETE
)


def allowed_operation(func):
    @functools.wraps(func)
    def wrapper(self, context, cluster, nodegroup, *args, **kwargs):
        # Before we begin we need to check the status
        # of the cluster. If the cluster is in a status
        # that does not allow nodegroup creation we just
        # fail.
        if ('status' in nodegroup
                and nodegroup.status not in ALLOWED_NODEGROUP_STATES):
            operation = _(
                '%(fname)s when nodegroup status is "%(status)s"'
            ) % {'fname': func.__name__, 'status': cluster.status}
            raise exception.NotSupported(operation=operation)
        return func(self, context, cluster, nodegroup, *args, **kwargs)

    return wrapper


@profiler.trace_cls("rpc")
class Handler(object):

    @allowed_operation
    def nodegroup_create(self, context, cluster, nodegroup):
        LOG.debug("nodegroup_conductor nodegroup_create")
        cluster.status = fields.ClusterStatus.UPDATE_IN_PROGRESS
        cluster.save()
        nodegroup.status = fields.ClusterStatus.CREATE_IN_PROGRESS
        nodegroup.create()

        try:
            cluster_driver = driver.Driver.get_driver_for_cluster(context,
                                                                  cluster)
            cluster_driver.create_nodegroup(context, cluster, nodegroup)
            nodegroup.save()
        except Exception as e:
            nodegroup.status = fields.ClusterStatus.CREATE_FAILED
            nodegroup.status_reason = str(e)
            nodegroup.save()
            cluster.status = fields.ClusterStatus.UPDATE_FAILED
            cluster.save()
            if isinstance(e, exc.HTTPBadRequest):
                e = exception.InvalidParameterValue(message=str(e))
                raise e
            raise
        return nodegroup

    @allowed_operation
    def nodegroup_update(self, context, cluster, nodegroup):
        LOG.debug("nodegroup_conductor nodegroup_update")
        cluster.status = fields.ClusterStatus.UPDATE_IN_PROGRESS
        cluster.save()
        nodegroup.status = fields.ClusterStatus.UPDATE_IN_PROGRESS

        try:
            cluster_driver = driver.Driver.get_driver_for_cluster(context,
                                                                  cluster)
            cluster_driver.update_nodegroup(context, cluster, nodegroup)
            nodegroup.save()
        except Exception as e:
            nodegroup.status = fields.ClusterStatus.UPDATE_FAILED
            nodegroup.status_reason = str(e)
            nodegroup.save()
            cluster.status = fields.ClusterStatus.UPDATE_FAILED
            cluster.save()
            if isinstance(e, exc.HTTPBadRequest):
                e = exception.InvalidParameterValue(message=str(e))
                raise e
            raise

        return nodegroup

    def nodegroup_delete(self, context, cluster, nodegroup):
        LOG.debug("nodegroup_conductor nodegroup_delete")
        cluster.status = fields.ClusterStatus.UPDATE_IN_PROGRESS
        cluster.save()
        nodegroup.status = fields.ClusterStatus.DELETE_IN_PROGRESS

        try:
            cluster_driver = driver.Driver.get_driver_for_cluster(context,
                                                                  cluster)
            cluster_driver.delete_nodegroup(context, cluster, nodegroup)
        except exc.HTTPNotFound:
            LOG.info('The nodegroup %s was not found during nodegroup'
                     ' deletion.', nodegroup.uuid)
            try:
                nodegroup.destroy()
            except exception.NodeGroupNotFound:
                LOG.info('The nodegroup %s has been deleted by others.',
                         nodegroup.uuid)
            return None
        except exc.HTTPConflict:
            raise exception.NgOperationInProgress(nodegroup=nodegroup.name)
        except Exception as e:
            nodegroup.status = fields.ClusterStatus.DELETE_FAILED
            nodegroup.status_reason = str(e)
            nodegroup.save()
            cluster.status = fields.ClusterStatus.UPDATE_FAILED
            cluster.save()
            raise
        return None
