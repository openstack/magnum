# Copyright 2013 - Red Hat, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import tempfile

import fixtures
from oslo.config import cfg
from oslo.db import options

from magnum.common import context
from magnum import objects
from magnum.objects.sqlalchemy import models

CONF = cfg.CONF


def dummy_context(user='test_username', tenant_id='test_tenant_id',
                  user_name='usr_name'):
    return context.RequestContext(user=user, tenant=tenant_id,
                                  user_name=user_name)


class Database(fixtures.Fixture):

    def __init__(self):
        super(Database, self).__init__()
        self.db_file = None
        with tempfile.NamedTemporaryFile(suffix='.sqlite',
                                         delete=False) as test_file:
            # note the temp file gets deleted by the NestedTempfile fixture.
            self.db_file = test_file.name
        objects.IMPL.cleanup()

    def setUp(self):
        super(Database, self).setUp()
        self.configure()
        self.addCleanup(objects.IMPL.cleanup)
        objects.IMPL.get_engine().connect()
        objects.load()
        models.Base.metadata.create_all(objects.IMPL.get_engine())

    def configure(self):
        options.cfg.set_defaults(options.database_opts,
                                 sqlite_synchronous=False)
        options.set_defaults(cfg.CONF,
                             connection='sqlite:///%s' % self.db_file,
                             sqlite_db=self.db_file)


def get_dummy_session():
    return objects.IMPL.get_session()


def create_models_from_data(model_cls, data, ctx):
    for d in data:
        mdl = model_cls()
        for key, value in d.items():
            setattr(mdl, key, value)
        mdl.create(ctx)
        d['id'] = mdl.id
