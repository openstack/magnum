# Copyright 2015 NEC Corporation.  All rights reserved.
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

from oslo_utils import timeutils
import pecan
from pecan import rest
import wsme
from wsme import types as wtypes
import wsmeext.pecan as wsme_pecan

from magnum.api.controllers import base
from magnum.api.controllers import link
from magnum.api.controllers.v1 import collection
from magnum.api.controllers.v1 import types
from magnum.api import utils as api_utils
from magnum.common import exception
from magnum import objects


class X509KeyPairPatchType(types.JsonPatchType):
    @staticmethod
    def mandatory_attrs():
        return ['/bay_uuid']


class X509KeyPair(base.APIBase):
    """API representation of a x509keypair.

    This class enforces type checking and value constraints, and converts
    between the internal object model and the API representation of a
    x509keypair.
    """

    _bay_uuid = None

    def _get_bay_uuid(self):
        return self._bay_uuid

    def _set_bay_uuid(self, value):
        if value and self._bay_uuid != value:
            try:
                bay = api_utils.get_rpc_resource('Bay', value)
                self._bay_uuid = bay.uuid
            except exception.BayNotFound as e:
                # Change error code because 404 (NotFound) is inappropriate
                # response for a POST request to create a Bay
                e.code = 400  # BadRequest
                raise e
        elif value == wtypes.Unset:
            self._bay_uuid = wtypes.Unset

    uuid = types.uuid
    """Unique UUID for this x509keypair"""

    name = wtypes.StringType(min_length=1, max_length=255)
    """Name of the x509keypair"""

    bay_uuid = wsme.wsproperty(wtypes.text, _get_bay_uuid,
                               _set_bay_uuid, mandatory=True)
    """The bay UUID or id"""

    links = wsme.wsattr([link.Link], readonly=True)
    """A list containing a self link and associated x509keypair links"""

    ca_cert = wtypes.StringType(min_length=1)
    """"The CA certificate"""

    certificate = wtypes.StringType(min_length=1)
    """The certificate"""

    private_key = wtypes.StringType(min_length=1)
    """The private key"""

    def __init__(self, **kwargs):
        super(X509KeyPair, self).__init__()

        self.fields = []
        for field in objects.X509KeyPair.fields:
            # Skip fields we do not expose.
            if not hasattr(self, field):
                continue
            self.fields.append(field)
            setattr(self, field, kwargs.get(field, wtypes.Unset))

    @staticmethod
    def _convert_with_links(x509keypair, url, expand=True):
        if not expand:
            x509keypair.unset_fields_except(['uuid', 'name', 'bay_uuid',
                                             'ca_cert', 'certificate',
                                             'private_key'])

        x509keypair.links = [link.Link.make_link('self', url,
                                                 'x509keypairs',
                                                 x509keypair.uuid),
                             link.Link.make_link('bookmark', url,
                                                 'x509keypairs',
                                                 x509keypair.uuid,
                                                 bookmark=True)]
        return x509keypair

    @classmethod
    def convert_with_links(cls, rpc_x509keypair, expand=True):
        x509keypair = X509KeyPair(**rpc_x509keypair.as_dict())
        return cls._convert_with_links(x509keypair,
                                       pecan.request.host_url, expand)

    @classmethod
    def sample(cls, expand=True):
        sample = cls(uuid='f978db47-9a37-4e9f-8572-804a10abc0aa',
                     name='MyX509KeyPair',
                     bay_uuid='7ae81bb3-dec3-4289-8d6c-da80bd8001ae',
                     created_at=timeutils.utcnow(),
                     ca_cert='AAA....AAA',
                     certificate='BBB....BBB',
                     private_key='CCC....CCC')
        return cls._convert_with_links(sample, 'http://localhost:9511', expand)


class X509KeyPairCollection(collection.Collection):
    """API representation of a collection of x509keypairs."""

    x509keypairs = [X509KeyPair]
    """A list containing x509keypairs objects"""

    def __init__(self, **kwargs):
        self._type = 'x509keypairs'

    @staticmethod
    def convert_with_links(rpc_x509keypairs, limit, url=None,
                           expand=False, **kwargs):
        collection = X509KeyPairCollection()
        collection.x509keypairs = [X509KeyPair.convert_with_links(p, expand)
                                   for p in rpc_x509keypairs]
        collection.next = collection.get_next(limit, url=url, **kwargs)
        return collection

    @classmethod
    def sample(cls):
        sample = cls()
        sample.x509keypairs = [X509KeyPair.sample(expand=False)]
        return sample


class X509KeyPairController(rest.RestController):
    """REST controller for X509KeyPair."""

    def __init__(self):
        super(X509KeyPairController, self).__init__()

    _custom_actions = {
        'detail': ['GET'],
    }

    def _get_x509keypairs_collection(self, marker, limit,
                                     sort_key, sort_dir, expand=False,
                                     resource_url=None):

        limit = api_utils.validate_limit(limit)
        sort_dir = api_utils.validate_sort_dir(sort_dir)

        marker_obj = None
        if marker:
            marker_obj = objects.X509KeyPair.get_by_uuid(pecan.request.context,
                                                         marker)

        x509keypairs = pecan.request.rpcapi.x509keypair_list(
            pecan.request.context, limit,
            marker_obj, sort_key=sort_key,
            sort_dir=sort_dir)

        return X509KeyPairCollection.convert_with_links(x509keypairs, limit,
                                                        url=resource_url,
                                                        expand=expand,
                                                        sort_key=sort_key,
                                                        sort_dir=sort_dir)

    @wsme_pecan.wsexpose(X509KeyPairCollection, types.uuid, int,
                         wtypes.text, wtypes.text)
    def get_all(self, marker=None, limit=None, sort_key='id',
                sort_dir='asc'):
        """Retrieve a list of x509keypairs.

        :param marker: pagination marker for large data sets.
        :param limit: maximum number of resources to return in a single result.
        :param sort_key: column to sort results by. Default: id.
        :param sort_dir: direction to sort. "asc" or "desc". Default: asc.
        """
        return self._get_x509keypairs_collection(marker, limit, sort_key,
                                                 sort_dir)

    @wsme_pecan.wsexpose(X509KeyPairCollection, types.uuid, int,
                         wtypes.text, wtypes.text)
    def detail(self, marker=None, limit=None, sort_key='id',
               sort_dir='asc'):
        """Retrieve a list of x509keypairs with detail.

        :param marker: pagination marker for large data sets.
        :param limit: maximum number of resources to return in a single result.
        :param sort_key: column to sort results by. Default: id.
        :param sort_dir: direction to sort. "asc" or "desc". Default: asc.
        """
        # NOTE(lucasagomes): /detail should only work against collections
        parent = pecan.request.path.split('/')[:-1][-1]
        if parent != "x509keypairs":
            raise exception.HTTPNotFound

        expand = True
        resource_url = '/'.join(['x509keypairs', 'detail'])
        return self._get_x509keypairs_collection(marker, limit,
                                                 sort_key, sort_dir, expand,
                                                 resource_url)

    @wsme_pecan.wsexpose(X509KeyPair, types.uuid_or_name)
    def get_one(self, x509keypair_ident):
        """Retrieve information about the given x509keypair.

        :param x509keypair_ident: UUID of a x509keypair or
        logical name of the x509keypair.
        """
        rpc_x509keypair = api_utils.get_rpc_resource('X509KeyPair',
                                                     x509keypair_ident)

        return X509KeyPair.convert_with_links(rpc_x509keypair)

    @wsme_pecan.wsexpose(X509KeyPair, body=X509KeyPair, status_code=201)
    def post(self, x509keypair):
        """Create a new x509keypair.

        :param x509keypair: a x509keypair within the request body.
        """
        x509keypair_dict = x509keypair.as_dict()
        context = pecan.request.context
        x509keypair_dict['project_id'] = context.project_id
        x509keypair_dict['user_id'] = context.user_id
        x509keypair_obj = objects.X509KeyPair(context, **x509keypair_dict)
        new_x509keypair = pecan.request.rpcapi.x509keypair_create(
            x509keypair_obj)
        # Set the HTTP Location Header
        pecan.response.location = link.build_url('x509keypairs',
                                                 new_x509keypair.uuid)
        return X509KeyPair.convert_with_links(new_x509keypair)

    @wsme_pecan.wsexpose(None, types.uuid_or_name, status_code=204)
    def delete(self, x509keypair_ident):
        """Delete a x509keypair.

        :param x509keypair_ident: UUID of a x509keypair or logical
        name of the x509keypair.
        """
        rpc_x509keypair = api_utils.get_rpc_resource('X509KeyPair',
                                                     x509keypair_ident)

        pecan.request.rpcapi.x509keypair_delete(rpc_x509keypair.uuid)
