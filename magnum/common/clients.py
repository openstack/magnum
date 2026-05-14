# Copyright 2014 - Rackspace Hosting.
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

from keystoneauth1.exceptions import catalog
from openstack import connection as sdk_connection
from oslo_log import log as logging

from magnum.common import exception
from magnum.common import keystone
import magnum.conf

CONF = magnum.conf.CONF
LOG = logging.getLogger(__name__)


class OpenStackClients(object):
    """Convenience class to create and cache client instances."""

    def __init__(self, context):
        self.context = context
        self._keystone = None
        self._glance = None
        self._barbican = None
        self._nova = None
        self._neutron = None
        self._octavia = None
        self._cinder = None

    def url_for(self, **kwargs):
        return self.keystone().session.get_endpoint(**kwargs)

    def magnum_url(self):
        endpoint_type = self._get_client_option('magnum', 'endpoint_type')
        region_name = self._get_client_option('magnum', 'region_name')
        try:
            return self.url_for(service_type='container-infra',
                                interface=endpoint_type,
                                region_name=region_name)
        except catalog.EndpointNotFound:
            url = self.url_for(service_type='container',
                               interface=endpoint_type,
                               region_name=region_name)
            LOG.warning('Service type "container" is deprecated and will '
                        'be removed in a subsequent release')
            return url

    def cinder_region_name(self):
        cinder_region_name = self._get_client_option('cinder', 'region_name')
        return self.keystone().get_validate_region_name(cinder_region_name)

    def keystone(self):
        if self._keystone:
            return self._keystone

        self._keystone = keystone.KeystoneClientV3(self.context)
        return self._keystone

    def _get_client_option(self, client, option):
        return getattr(getattr(CONF, '%s_client' % client), option)

    @exception.wrap_keystone_exception
    def octavia(self):
        if self._octavia:
            return self._octavia

        region_name = self._get_client_option('octavia', 'region_name')
        endpoint_type = self._get_client_option('octavia', 'endpoint_type')
        endpoint = self.url_for(service_type='load-balancer',
                                interface=endpoint_type,
                                region_name=region_name)
        session = self.keystone().session
        conn = sdk_connection.Connection(
            session=session,
            **{'load_balancer_endpoint_override': endpoint}
        )
        return conn.load_balancer

    @exception.wrap_keystone_exception
    def glance(self):
        if self._glance:
            return self._glance

        endpoint_type = self._get_client_option('glance', 'endpoint_type')
        region_name = self._get_client_option('glance', 'region_name')
        endpoint = self.url_for(service_type='image',
                                interface=endpoint_type,
                                region_name=region_name)
        session = self.keystone().session
        conn = sdk_connection.Connection(
            session=session,
            **{'image_endpoint_override': endpoint}
        )
        self._glance = conn.image
        return self._glance

    @exception.wrap_keystone_exception
    def barbican(self):
        if self._barbican:
            return self._barbican

        endpoint_type = self._get_client_option('barbican', 'endpoint_type')
        region_name = self._get_client_option('barbican', 'region_name')
        endpoint = self.url_for(service_type='key-manager',
                                interface=endpoint_type,
                                region_name=region_name)
        session = self.keystone().session
        conn = sdk_connection.Connection(
            session=session,
            **{'key_manager_endpoint_override': endpoint}
        )
        self._barbican = conn.key_manager

        return self._barbican

    @exception.wrap_keystone_exception
    def nova(self):
        if self._nova:
            return self._nova
        endpoint_type = self._get_client_option('nova', 'endpoint_type')
        region_name = self._get_client_option('nova', 'region_name')
        endpoint = self.url_for(service_type='compute',
                                interface=endpoint_type,
                                region_name=region_name)
        session = self.keystone().session
        conn = sdk_connection.Connection(
            session=session,
            **{'compute_endpoint_override': endpoint}
        )
        self._nova = conn.compute
        return self._nova

    @exception.wrap_keystone_exception
    def neutron(self):
        if self._neutron:
            return self._neutron
        endpoint_type = self._get_client_option('neutron', 'endpoint_type')
        region_name = self._get_client_option('neutron', 'region_name')
        endpoint = self.url_for(service_type='network',
                                interface=endpoint_type,
                                region_name=region_name)
        session = self.keystone().session
        conn = sdk_connection.Connection(
            session=session,
            **{'network_endpoint_override': endpoint}
        )
        self._neutron = conn.network
        return self._neutron

    @exception.wrap_keystone_exception
    def cinder(self):
        if self._cinder:
            return self._cinder
        endpoint_type = self._get_client_option('cinder', 'endpoint_type')
        region_name = self._get_client_option('cinder', 'region_name')
        endpoint = self.url_for(service_type='block-storage',
                                interface=endpoint_type,
                                region_name=region_name)
        session = self.keystone().session
        conn = sdk_connection.Connection(
            session=session,
            **{'block_storage_endpoint_override': endpoint}
        )
        self._cinder = conn.block_storage
        return self._cinder
