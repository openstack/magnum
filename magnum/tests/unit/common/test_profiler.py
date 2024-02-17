# Copyright 2017 OpenStack Foundation
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

import importlib
import inspect
from unittest import mock

from oslo_config import cfg
from oslo_utils import importutils
from osprofiler import initializer as profiler_init
from osprofiler import opts as profiler_opts

from magnum.common import profiler
from magnum import conf
from magnum.tests import base


class TestProfiler(base.TestCase):
    def test_all_public_methods_are_traced(self):
        profiler_opts.set_defaults(conf.CONF)
        self.config(enabled=True,
                    group='profiler')

        classes = [
            'magnum.conductor.api.API',
            'magnum.conductor.api.ListenerAPI',
            'magnum.conductor.handlers.ca_conductor.Handler',
            'magnum.conductor.handlers.cluster_conductor.Handler',
            'magnum.conductor.handlers.conductor_listener.Handler',
            'magnum.conductor.handlers.indirection_api.Handler',
            'magnum.service.periodic.MagnumPeriodicTasks',
        ]
        for clsname in classes:
            # give the metaclass and trace_cls() decorator a chance to patch
            # methods of the classes above
            importlib.reload(
                importutils.import_module(clsname.rsplit('.', 1)[0]))
            cls = importutils.import_class(clsname)

            for attr, obj in cls.__dict__.items():
                # only public methods are traced
                if attr.startswith('_'):
                    continue
                # only checks callables
                if not (inspect.ismethod(obj) or inspect.isfunction(obj)):
                    continue
                # osprofiler skips static methods
                if isinstance(obj, staticmethod):
                    continue

                self.assertTrue(getattr(obj, '__traced__', False), obj)

    @mock.patch.object(profiler_init, 'init_from_conf')
    def test_setup_profiler(self, mock_init):
        self.config(enabled=True,
                    group='profiler')

        profiler.setup('foo', 'localhost')

        mock_init.assert_called_once_with(conf=conf.CONF,
                                          context=mock.ANY,
                                          project="magnum",
                                          service='foo',
                                          host='localhost')

    @mock.patch.object(profiler_init, 'init_from_conf')
    @mock.patch.object(conf, 'CONF', new=cfg.ConfigOpts())
    def test_setup_profiler_without_osprofiler(self, mock_init):
        profiler.setup('foo', 'localhost')
        self.assertEqual(False, mock_init.called)
