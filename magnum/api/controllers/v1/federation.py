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

import uuid

from oslo_log import log as logging
import pecan
import wsme
from wsme import types as wtypes

from magnum.api import attr_validator
from magnum.api.controllers import base
from magnum.api.controllers import link
from magnum.api.controllers.v1 import collection
from magnum.api.controllers.v1 import types
from magnum.api import expose
from magnum.api import utils as api_utils
from magnum.api import validation
from magnum.common import exception
from magnum.common import name_generator
from magnum.common import policy
import magnum.conf
from magnum import objects
from magnum.objects import fields

LOG = logging.getLogger(__name__)
CONF = magnum.conf.CONF


class FederationID(wtypes.Base):
    """API representation of a federation ID

    This class enforces type checking and value constraints, and converts
    between the internal object model and the API representation of a
    federation ID.
    """
    uuid = types.uuid

    def __init__(self, uuid):
        self.uuid = uuid


class Federation(base.APIBase):
    """API representation of a federation.

    This class enforces type checking and value constraints, and converts
    between the internal object model and the API representation of a
    Federation.
    """

    # Unique UUID for this federation.
    uuid = types.uuid

    # Name of this federation, max length is limited to 242 because heat stack
    # requires max length limit to 255, and Magnum amend a uuid length.
    name = wtypes.StringType(min_length=1, max_length=242,
                             pattern='^[a-zA-Z][a-zA-Z0-9_.-]*$')

    # UUID of the hostcluster of the federation, i.e. the cluster that
    # hosts the COE Federated API.
    hostcluster_id = wsme.wsattr(wtypes.text)

    # List of UUIDs of all the member clusters of the federation.
    member_ids = wsme.wsattr([wtypes.text])

    # Status of the federation.
    status = wtypes.Enum(wtypes.text, *fields.FederationStatus.ALL)

    # Status reason of the federation.
    status_reason = wtypes.text

    # Set of federation metadata (COE-specific in some cases).
    properties = wtypes.DictType(wtypes.text, wtypes.text)

    # A list containing a self link and associated federations links
    links = wsme.wsattr([link.Link], readonly=True)

    def __init__(self, **kwargs):
        super(Federation, self).__init__()
        self.fields = []
        for field in objects.Federation.fields:
            # Skip fields we do not expose.
            if not hasattr(self, field):
                continue
            self.fields.append(field)
            setattr(self, field, kwargs.get(field, wtypes.Unset))

    @staticmethod
    def _convert_with_links(federation, url, expand=True):
        if not expand:
            federation.unset_fields_except(['uuid', 'name', 'hostcluster_id',
                                            'member_ids', 'status',
                                            'properties'])

        federation.links = [link.Link.make_link('self', url, 'federations',
                                                federation.uuid),
                            link.Link.make_link('bookmark', url, 'federations',
                                                federation.uuid,
                                                bookmark=True)]
        return federation

    @classmethod
    def convert_with_links(cls, rpc_federation, expand=True):
        federation = Federation(**rpc_federation.as_dict())
        return cls._convert_with_links(federation, pecan.request.host_url,
                                       expand)

    @classmethod
    def sample(cls, expand=True):
        sample = cls(uuid='4221a353-8368-475f-b7de-3429d3f724b3',
                     name='example',
                     hostcluster_id='49dc23f5-ffc9-40c3-9d34-7be7f9e34d63',
                     member_ids=['49dc23f5-ffc9-40c3-9d34-7be7f9e34d63',
                                 'f2439bcf-02a2-4278-9d8a-f07a2042230a',
                                 'e549e0a5-3d3c-406f-bd7c-0e0182fb211c'],
                     properties={'dns-zone': 'example.com.'},
                     status=fields.FederationStatus.CREATE_COMPLETE,
                     status_reason="CREATE completed successfully")
        return cls._convert_with_links(sample, 'http://localhost:9511', expand)


class FederationPatchType(types.JsonPatchType):
    _api_base = Federation

    @staticmethod
    def internal_attrs():
        """"Returns a list of internal attributes.

        Internal attributes can't be added, replaced or removed.
        """
        internal_attrs = []
        return types.JsonPatchType.internal_attrs() + internal_attrs


class FederationCollection(collection.Collection):
    """API representation of a collection of federations."""

    # A list containing federation objects.
    federations = [Federation]

    def __init__(self, **kwargs):
        self._type = 'federations'

    @staticmethod
    def convert_with_links(rpc_federation, limit, url=None, expand=False,
                           **kwargs):
        collection = FederationCollection()
        collection.federations = [Federation.convert_with_links(p, expand)
                                  for p in rpc_federation]
        collection.next = collection.get_next(limit, url=url, **kwargs)
        return collection

    @classmethod
    def sample(cls):
        sample = cls()
        sample.federations = [Federation.sample(expand=False)]
        return sample


class FederationsController(base.Controller):
    """REST controller for federations."""

    def __init__(self):
        super(FederationsController, self).__init__()

    _custom_actions = {
        'detail': ['GET'],
    }

    def _generate_name_for_federation(self, context):
        """Generate a random name like: phi-17-federation."""
        name_gen = name_generator.NameGenerator()
        name = name_gen.generate()
        return name + '-federation'

    def _get_federation_collection(self, marker, limit,
                                   sort_key, sort_dir, expand=False,
                                   resource_url=None):
        limit = api_utils.validate_limit(limit)
        sort_dir = api_utils.validate_sort_dir(sort_dir)

        marker_obj = None
        if marker:
            marker_obj = objects.Federation.get_by_uuid(pecan.request.context,
                                                        marker)

        federations = objects.Federation.list(pecan.request.context, limit,
                                              marker_obj, sort_key=sort_key,
                                              sort_dir=sort_dir)

        return FederationCollection.convert_with_links(federations, limit,
                                                       url=resource_url,
                                                       expand=expand,
                                                       sort_key=sort_key,
                                                       sort_dir=sort_dir)

    @expose.expose(FederationCollection, types.uuid, int, wtypes.text,
                   wtypes.text)
    def get_all(self, marker=None, limit=None, sort_key='id',
                sort_dir='asc'):
        """Retrieve a list of federations.

        :param marker: pagination marker for large data sets.
        :param limit: maximum number of resources to return in a single result.
        :param sort_key: column to sort results by. Default: id.
        :param sort_dir: direction to sort. "asc" or "desc". Default: asc.
        """
        context = pecan.request.context
        policy.enforce(context, 'federation:get_all',
                       action='federation:get_all')
        return self._get_federation_collection(marker, limit, sort_key,
                                               sort_dir)

    @expose.expose(FederationCollection, types.uuid, int, wtypes.text,
                   wtypes.text)
    def detail(self, marker=None, limit=None, sort_key='id',
               sort_dir='asc'):
        """Retrieve a list of federation with detail.

        :param marker: pagination marker for large data sets.
        :param limit: maximum number of resources to return in a single result.
        :param sort_key: column to sort results by. Default: id.
        :param sort_dir: direction to sort. "asc" or "desc". Default: asc.
        """
        context = pecan.request.context
        policy.enforce(context, 'federation:detail',
                       action='federation:detail')

        # NOTE(lucasagomes): /detail should only work against collections
        parent = pecan.request.path.split('/')[:-1][-1]
        if parent != "federations":
            raise exception.HTTPNotFound

        expand = True
        resource_url = '/'.join(['federations', 'detail'])
        return self._get_federation_collection(marker, limit,
                                               sort_key, sort_dir, expand,
                                               resource_url)

    @expose.expose(Federation, types.uuid_or_name)
    def get_one(self, federation_ident):
        """Retrieve information about a given Federation.

        :param federation_ident: UUID or logical name of the Federation.
        """
        context = pecan.request.context
        federation = api_utils.get_resource('Federation', federation_ident)
        policy.enforce(context, 'federation:get', federation.as_dict(),
                       action='federation:get')

        federation = Federation.convert_with_links(federation)

        return federation

    @expose.expose(FederationID, body=Federation, status_code=202)
    def post(self, federation):
        """Create a new federation.

        :param federation: a federation within the request body.
        """
        context = pecan.request.context
        policy.enforce(context, 'federation:create',
                       action='federation:create')

        federation_dict = federation.as_dict()

        # Validate `hostcluster_id`
        hostcluster_id = federation_dict.get('hostcluster_id')
        attr_validator.validate_federation_hostcluster(hostcluster_id)

        # Validate `properties` dict.
        properties_dict = federation_dict.get('properties')
        attr_validator.validate_federation_properties(properties_dict)

        federation_dict['project_id'] = context.project_id

        # If no name is specified, generate a random human-readable name
        name = (federation_dict.get('name') or
                self._generate_name_for_federation(context))
        federation_dict['name'] = name

        new_federation = objects.Federation(context, **federation_dict)
        new_federation.uuid = uuid.uuid4()

        # TODO(clenimar): remove hard-coded `create_timeout`.
        pecan.request.rpcapi.federation_create_async(new_federation,
                                                     create_timeout=15)

        return FederationID(new_federation.uuid)

    @expose.expose(FederationID, types.uuid_or_name, types.boolean,
                   body=[FederationPatchType], status_code=202)
    def patch(self, federation_ident, rollback=False, patch=None):
        """Update an existing Federation.

        Please note that the join/unjoin operation is performed by patching
        `member_ids`.

        :param federation_ident: UUID or logical name of a federation.
        :param rollback: whether to rollback federation on update failure.
        :param patch: a json PATCH document to apply to this federation.
        """
        federation = self._patch(federation_ident, patch)
        pecan.request.rpcapi.federation_update_async(federation, rollback)
        return FederationID(federation.uuid)

    def _patch(self, federation_ident, patch):
        context = pecan.request.context
        federation = api_utils.get_resource('Federation', federation_ident)
        policy.enforce(context, 'federation:update', federation.as_dict(),
                       action='federation:update')

        # NOTE(clenimar): Magnum does not allow one to append items to existing
        # fields through an `add` operation using HTTP PATCH (please check
        # `magnum.api.utils.apply_jsonpatch`). In order to perform the join
        # and unjoin operations, intercept the original JSON PATCH document
        # and change the operation from either `add` or `remove` to `replace`.
        patch_path = patch[0].get('path')
        patch_value = patch[0].get('value')
        patch_op = patch[0].get('op')

        if patch_path == '/member_ids':
            if patch_op == 'add' and patch_value is not None:
                patch = self._join_wrapper(federation_ident, patch)
            elif patch_op == 'remove' and patch_value is not None:
                patch = self._unjoin_wrapper(federation_ident, patch)

        try:
            federation_dict = federation.as_dict()
            new_federation = Federation(
                **api_utils.apply_jsonpatch(federation_dict, patch))
        except api_utils.JSONPATCH_EXCEPTIONS as e:
            raise exception.PatchError(patch=patch, reason=e)

        # Retrieve only what changed after the patch.
        delta = self._update_changed_fields(federation, new_federation)
        validation.validate_federation_properties(delta)

        return federation

    def _update_changed_fields(self, federation, new_federation):
        """Update only the patches that were modified and return the diff."""
        for field in objects.Federation.fields:
            try:
                patch_val = getattr(new_federation, field)
            except AttributeError:
                # Ignore fields that aren't exposed in the API
                continue
            if patch_val == wtypes.Unset:
                patch_val = None
            if federation[field] != patch_val:
                federation[field] = patch_val

        return federation.obj_what_changed()

    def _join_wrapper(self, federation_ident, patch):
        """Intercept PATCH JSON documents for join operations.

        Take a PATCH JSON document with `add` operation::
            {
                'op': 'add',
                'value': 'new_member_id',
                'path': '/member_ids'
            }
        and transform it into a document with `replace` operation::
            {
                'op': 'replace',
                'value': ['current_member_id1', ..., 'new_member_id'],
                'path': '/member_ids'
            }
        """
        federation = api_utils.get_resource('Federation', federation_ident)
        new_member_uuid = patch[0]['value']

        # Check if the cluster exists
        c = objects.Cluster.get_by_uuid(pecan.request.context, new_member_uuid)

        # Check if the cluster is already a member of the federation
        if new_member_uuid not in federation.member_ids and c is not None:
            # Retrieve all current members
            members = federation.member_ids
            # Add the new member
            members.append(c.uuid)
        else:
            kw = {'uuid': new_member_uuid, 'federation_name': federation.name}
            raise exception.MemberAlreadyExists(**kw)

        # Set `value` to the updated member list. Change `op` to `replace`
        patch[0]['value'] = members
        patch[0]['op'] = 'replace'

        return patch

    def _unjoin_wrapper(self, federation_ident, patch):
        """Intercept PATCH JSON documents for unjoin operations.

        Take a PATCH JSON document with `remove` operation::
            {
                'op': 'remove',
                'value': 'former_member_id',
                'path': '/member_ids'
            }
        and transform it into a document with `replace` operation::
            {
                'op': 'replace',
                'value': ['current_member_id1', ..., 'current_member_idn'],
                'path': '/member_ids'
            }
        """
        federation = api_utils.get_resource('Federation', federation_ident)
        cluster_uuid = patch[0]['value']

        # Check if the cluster exists
        c = objects.Cluster.get_by_uuid(pecan.request.context, cluster_uuid)

        # Check if the cluster is a member cluster and if it exists
        if cluster_uuid in federation.member_ids and c is not None:
            # Retrieve all current members
            members = federation.member_ids
            # Unjoin the member
            members.remove(cluster_uuid)
        else:
            raise exception.HTTPNotFound("Cluster %s is not a member of the "
                                         "federation %s." % (cluster_uuid,
                                                             federation.name))

        # Set `value` to the updated member list. Change `op` to `replace`
        patch[0]['value'] = members
        patch[0]['op'] = 'replace'

        return patch

    @expose.expose(None, types.uuid_or_name, status_code=204)
    def delete(self, federation_ident):
        """Delete a federation.

        :param federation_ident: UUID of federation or logical name
                                 of the federation.
        """
        context = pecan.request.context
        federation = api_utils.get_resource('Federation', federation_ident)
        policy.enforce(context, 'federation:delete', federation.as_dict(),
                       action='federation:delete')

        pecan.request.rpcapi.federation_delete_async(federation.uuid)
