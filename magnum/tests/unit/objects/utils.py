# Copyright 2014 Rackspace Hosting
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
"""Magnum object test utilities."""


import datetime

import netaddr
from oslo_utils import timeutils

from magnum.common import exception
from magnum.i18n import _
from magnum import objects
from magnum.tests.unit.db import utils as db_utils


def get_test_cluster_template(context, **kw):
    """Return a ClusterTemplate object with appropriate attributes.

    NOTE: The object leaves the attributes marked as changed, such
    that a create() could be used to commit it to the DB.
    """
    db_cluster_template = db_utils.get_test_cluster_template(**kw)
    cluster_template = objects.ClusterTemplate(context)
    # Let DB generate ID if it isn't specified explicitly
    if 'id' not in kw:
        del db_cluster_template['id']

    for key in db_cluster_template:
        setattr(cluster_template, key, db_cluster_template[key])
    return cluster_template


def create_test_cluster_template(context, **kw):
    """Create and return a test ClusterTemplate object.

    Create a ClusterTemplate in the DB and return a ClusterTemplate object
    with appropriate attributes.
    """
    cluster_template = get_test_cluster_template(context, **kw)
    try:
        cluster_template.create()
    except exception.ClusterTemplateAlreadyExists:
        cluster_template = objects.ClusterTemplate.get(context,
                                                       cluster_template.uuid)
    return cluster_template


def get_test_cluster(context, **kw):
    """Return a Cluster object with appropriate attributes.

    NOTE: The object leaves the attributes marked as changed, such
    that a create() could be used to commit it to the DB.
    """
    db_cluster = db_utils.get_test_cluster(**kw)
    # Let DB generate ID if it isn't specified explicitly
    if 'id' not in kw:
        del db_cluster['id']
    cluster = objects.Cluster(context)
    for key in db_cluster:
        setattr(cluster, key, db_cluster[key])
    return cluster


def create_test_cluster(context, **kw):
    """Create and return a test Cluster object.

    Create a Cluster in the DB and return a Cluster object with appropriate
    attributes.
    """
    cluster = get_test_cluster(context, **kw)
    create_test_cluster_template(context, uuid=cluster['cluster_template_id'],
                                 coe=kw.get('coe', 'kubernetes'),
                                 tls_disabled=kw.get('tls_disabled'))
    kw.update({'cluster_id': cluster['uuid']})
    db_utils.create_nodegroups_for_cluster(**kw)
    cluster.create()
    return cluster


def get_test_quota(context, **kw):
    """Return a Quota object with appropriate attributes.

    NOTE: The object leaves the attributes marked as changed, such
    that a create() could be used to commit it to the DB.
    """
    db_quota = db_utils.get_test_quota(**kw)
    # Let DB generate ID if it isn't specified explicitly
    if 'id' not in kw:
        del db_quota['id']
    quota = objects.Quota(context)
    for key in db_quota:
        setattr(quota, key, db_quota[key])
    return quota


def create_test_quota(context, **kw):
    """Create and return a test Quota object.

    Create a quota in the DB and return a Quota object with appropriate
    attributes.
    """
    quota = get_test_quota(context, **kw)
    quota.create()
    return quota


def get_test_x509keypair(context, **kw):
    """Return a X509KeyPair object with appropriate attributes.

    NOTE: The object leaves the attributes marked as changed, such
    that a create() could be used to commit it to the DB.
    """
    db_x509keypair = db_utils.get_test_x509keypair(**kw)
    # Let DB generate ID if it isn't specified explicitly
    if 'id' not in kw:
        del db_x509keypair['id']
    x509keypair = objects.X509KeyPair(context)
    for key in db_x509keypair:
        setattr(x509keypair, key, db_x509keypair[key])
    return x509keypair


def create_test_x509keypair(context, **kw):
    """Create and return a test x509keypair object.

    Create a x509keypair in the DB and return a X509KeyPair object with
    appropriate attributes.
    """
    x509keypair = get_test_x509keypair(context, **kw)
    x509keypair.create()
    return x509keypair


def get_test_magnum_service_object(context, **kw):
    """Return a test magnum_service object.

    Get a magnum_service from DB layer and return an object with
    appropriate attributes.
    """
    db_magnum_service = db_utils.get_test_magnum_service(**kw)
    magnum_service = objects.MagnumService(context)
    for key in db_magnum_service:
        setattr(magnum_service, key, db_magnum_service[key])
    return magnum_service


def get_test_nodegroup(context, **kw):
    db_nodegroup = db_utils.get_test_nodegroup(**kw)
    nodegroup = objects.NodeGroup(context)
    for key in db_nodegroup:
        setattr(nodegroup, key, db_nodegroup[key])
    return nodegroup


def create_test_nodegroup(context, **kw):
    nodegroup = get_test_nodegroup(context, **kw)
    nodegroup.create()
    return nodegroup


def get_test_federation(context, **kw):
    """Return a Federation object with appropriate attributes.

    NOTE: The object leaves the attributes marked as changed, such
    that a create() could be used to commit it to the DB.
    """
    db_federation = db_utils.get_test_federation(**kw)
    # Let DB generate ID if it isn't specified explicitly
    if 'id' not in kw:
        del db_federation['id']
    federation = objects.Federation(context)
    for key in db_federation:
        setattr(federation, key, db_federation[key])
    return federation


def create_test_federation(context, **kw):
    """Create and return a test Federation object.

    Create a Federation in the DB and return a Federation object with
    appropriate attributes.
    """
    federation = get_test_federation(context, **kw)
    federation.create()
    return federation


def datetime_or_none(dt):
    """Validate a datetime or None value."""
    if dt is None:
        return None
    elif isinstance(dt, datetime.datetime):
        if dt.utcoffset() is None:
            # NOTE(danms): Legacy objects from sqlalchemy are stored in UTC,
            # but are returned without a timezone attached.
            # As a transitional aid, assume a tz-naive object is in UTC.
            return dt.replace(tzinfo=datetime.timezone.utc)
        else:
            return dt
    raise ValueError(_("A datetime.datetime is required here"))


def datetime_or_str_or_none(val):
    if isinstance(val, str):
        return timeutils.parse_isotime(val)
    return datetime_or_none(val)


def int_or_none(val):
    """Attempt to parse an integer value, or None."""
    if val is None:
        return val
    else:
        return int(val)


def str_or_none(val):
    """Attempt to stringify a value to unicode, or None."""
    if val is None:
        return val
    else:
        return str(val)


def ip_or_none(version):
    """Return a version-specific IP address validator."""
    def validator(val, version=version):
        if val is None:
            return val
        else:
            return netaddr.IPAddress(val, version=version)
    return validator


def dt_serializer(name):
    """Return a datetime serializer for a named attribute."""
    def serializer(self, name=name):
        if getattr(self, name) is not None:
            return datetime.datetime.isoformat(getattr(self, name))
        else:
            return None
    return serializer


def dt_deserializer(instance, val):
    """A deserializer method for datetime attributes."""
    if val is None:
        return None
    else:
        return timeutils.parse_isotime(val)
