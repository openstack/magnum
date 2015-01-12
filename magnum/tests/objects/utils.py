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

from magnum import objects
from magnum.tests.db import utils as db_utils


def get_test_baymodel(ctxt, **kw):
    """Return a BayModel object with appropriate attributes.

    NOTE: The object leaves the attributes marked as changed, such
    that a create() could be used to commit it to the DB.
    """
    db_baymodel = db_utils.get_test_baymodel(**kw)
    # Let DB generate ID if it isn't specified explicitly
    if 'id' not in kw:
        del db_baymodel['id']
    baymodel = objects.BayModel(ctxt)
    for key in db_baymodel:
        setattr(baymodel, key, db_baymodel[key])
    return baymodel


def create_test_baymodel(ctxt, **kw):
    """Create and return a test baymodel object.

    Create a baymodel in the DB and return a BayModel object with appropriate
    attributes.
    """
    baymodel = get_test_baymodel(ctxt, **kw)
    baymodel.create()
    return baymodel


def get_test_bay(ctxt, **kw):
    """Return a Bay object with appropriate attributes.

    NOTE: The object leaves the attributes marked as changed, such
    that a create() could be used to commit it to the DB.
    """
    db_bay = db_utils.get_test_bay(**kw)
    # Let DB generate ID if it isn't specified explicitly
    if 'id' not in kw:
        del db_bay['id']
    bay = objects.Bay(ctxt)
    for key in db_bay:
        setattr(bay, key, db_bay[key])
    return bay


def create_test_bay(ctxt, **kw):
    """Create and return a test bay object.

    Create a bay in the DB and return a Bay object with appropriate
    attributes.
    """
    bay = get_test_bay(ctxt, **kw)
    bay.create()
    return bay