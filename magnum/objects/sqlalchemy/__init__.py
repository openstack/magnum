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

import sys

from oslo.config import cfg
from oslo.db.sqlalchemy import session


_FACADE = None


def get_facade():
    global _FACADE

    if not _FACADE:
        _FACADE = session.EngineFacade.from_config(cfg.CONF)
    return _FACADE

get_engine = lambda: get_facade().get_engine()
get_session = lambda: get_facade().get_session()


def get_backend():
    """The backend is this module itself."""
    return sys.modules[__name__]


def cleanup():
    global _FACADE

    if _FACADE:
        _FACADE._session_maker.close_all()
        _FACADE.get_engine().dispose()
        _FACADE = None


def load():
    """Activate the sqlalchemy backend."""
    from magnum import objects
    from magnum.objects import bay as abstract_bay
    from magnum.objects import container as abstract_container
    from magnum.objects.sqlalchemy import bay
    from magnum.objects.sqlalchemy import container

    objects.registry.add(abstract_bay.Bay, bay.Bay)
    objects.registry.add(abstract_bay.BayList, bay.BayList)
    objects.registry.add(abstract_container.Container, container.Container)
    objects.registry.add(abstract_container.ContainerList,
                         container.ContainerList)