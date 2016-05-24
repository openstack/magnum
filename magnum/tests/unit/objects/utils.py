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

import iso8601
import netaddr
from oslo_utils import timeutils
import six

from magnum.common import exception
from magnum.i18n import _
from magnum import objects
from magnum.tests.unit.db import utils as db_utils


def get_test_baymodel(context, **kw):
    """Return a BayModel object with appropriate attributes.

    NOTE: The object leaves the attributes marked as changed, such
    that a create() could be used to commit it to the DB.
    """
    db_baymodel = db_utils.get_test_baymodel(**kw)
    # Let DB generate ID if it isn't specified explicitly
    if 'id' not in kw:
        del db_baymodel['id']
    baymodel = objects.BayModel(context)
    for key in db_baymodel:
        setattr(baymodel, key, db_baymodel[key])
    return baymodel


def create_test_baymodel(context, **kw):
    """Create and return a test baymodel object.

    Create a baymodel in the DB and return a BayModel object with appropriate
    attributes.
    """
    baymodel = get_test_baymodel(context, **kw)
    try:
        baymodel.create()
    except exception.BayModelAlreadyExists:
        baymodel = objects.BayModel.get(context, baymodel.uuid)
    return baymodel


def get_test_bay(context, **kw):
    """Return a Bay object with appropriate attributes.

    NOTE: The object leaves the attributes marked as changed, such
    that a create() could be used to commit it to the DB.
    """
    db_bay = db_utils.get_test_bay(**kw)
    # Let DB generate ID if it isn't specified explicitly
    if 'id' not in kw:
        del db_bay['id']
    bay = objects.Bay(context)
    for key in db_bay:
        setattr(bay, key, db_bay[key])
    return bay


def create_test_bay(context, **kw):
    """Create and return a test bay object.

    Create a bay in the DB and return a Bay object with appropriate
    attributes.
    """
    bay = get_test_bay(context, **kw)
    create_test_baymodel(context, uuid=bay['baymodel_id'],
                         coe=kw.get('coe', 'swarm'))
    bay.create()
    return bay


def get_test_rc(context, **kw):
    """Return a ReplicationController object with appropriate attributes.

    NOTE: The object leaves the attributes marked as changed, such
    that a create() could be used to commit it to the DB.
    """
    db_rc = db_utils.get_test_rc(**kw)
    # Let DB generate ID if it isn't specified explicitly
    if 'id' not in kw:
        del db_rc['id']
    rc = objects.ReplicationController(context)
    for key in db_rc:
        setattr(rc, key, db_rc[key])
    return rc


def create_test_rc(context, **kw):
    """Create and return a test ReplicationController object.

    Create a replication controller in the DB and return a
    ReplicationController object with appropriate attributes.
    """
    rc = get_test_rc(context, **kw)
    rc.manifest = '{"foo": "bar"}'
    return rc


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


def create_test_container(context, **kw):
    """Create and return a test container object.

    Create a container in the DB and return a container object with
    appropriate attributes.
    """
    container = get_test_container(context, **kw)
    container.create()
    return container


def get_test_container(context, **kw):
    """Return a test container object with appropriate attributes.

    NOTE: The object leaves the attributes marked as changed, such
    that a create() could be used to commit it to the DB.
    """
    db_container = db_utils.get_test_container(**kw)
    container = objects.Container(context)
    for key in db_container:
        setattr(container, key, db_container[key])
    return container


def datetime_or_none(dt):
    """Validate a datetime or None value."""
    if dt is None:
        return None
    elif isinstance(dt, datetime.datetime):
        if dt.utcoffset() is None:
            # NOTE(danms): Legacy objects from sqlalchemy are stored in UTC,
            # but are returned without a timezone attached.
            # As a transitional aid, assume a tz-naive object is in UTC.
            return dt.replace(tzinfo=iso8601.iso8601.Utc())
        else:
            return dt
    raise ValueError(_("A datetime.datetime is required here"))


def datetime_or_str_or_none(val):
    if isinstance(val, six.string_types):
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
        return six.text_type(val)


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
