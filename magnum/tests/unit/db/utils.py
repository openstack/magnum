# Copyright 2015 OpenStack Foundation
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
"""Magnum test utilities."""


from magnum.db import api as db_api


def get_test_baymodel(**kw):
    return {
        'id': kw.get('id', 32),
        'project_id': kw.get('project_id', 'fake_project'),
        'user_id': kw.get('user_id', 'fake_user'),
        'uuid': kw.get('uuid', 'e74c40e0-d825-11e2-a28f-0800200c9a66'),
        'name': kw.get('name', 'baymodel1'),
        'image_id': kw.get('image_id', 'ubuntu'),
        'flavor_id': kw.get('flavor_id', 'm1.small'),
        'master_flavor_id': kw.get('master_flavor_id', 'm1.small'),
        'keypair_id': kw.get('keypair_id', 'keypair1'),
        'external_network_id': kw.get('external_network_id',
                                      'd1f02cfb-d27f-4068-9332-84d907cb0e2e'),
        'fixed_network': kw.get('fixed_network', 'private'),
        'network_driver': kw.get('network_driver'),
        'volume_driver': kw.get('volume_driver'),
        'dns_nameserver': kw.get('dns_nameserver', '8.8.1.1'),
        'apiserver_port': kw.get('apiserver_port', 8080),
        'docker_volume_size': kw.get('docker_volume_size', 20),
        'docker_storage_driver': kw.get('docker_storage_driver',
                                        'devicemapper'),
        'cluster_distro': kw.get('cluster_distro', 'fedora-atomic'),
        'coe': kw.get('coe', 'swarm'),
        'created_at': kw.get('created_at'),
        'updated_at': kw.get('updated_at'),
        'labels': kw.get('labels', {'key1': 'val1', 'key2': 'val2'}),
        'http_proxy': kw.get('http_proxy', 'fake_http_proxy'),
        'https_proxy': kw.get('https_proxy', 'fake_https_proxy'),
        'no_proxy': kw.get('no_proxy', 'fake_no_proxy'),
        'registry_enabled': kw.get('registry_enabled', False),
        'tls_disabled': kw.get('tls_disabled', False),
        'public': kw.get('public', False),
        'server_type': kw.get('server_type', 'vm'),
        'insecure_registry': kw.get('insecure_registry', '10.0.0.1:5000'),
    }


def create_test_baymodel(**kw):
    """Create test baymodel entry in DB and return BayModel DB object.

    Function to be used to create test BayModel objects in the database.
    :param kw: kwargs with overriding values for baymodel's attributes.
    :returns: Test BayModel DB object.
    """
    baymodel = get_test_baymodel(**kw)
    # Let DB generate ID if it isn't specified explicitly
    if 'id' not in kw:
        del baymodel['id']
    dbapi = db_api.get_instance()
    return dbapi.create_baymodel(baymodel)


def get_test_bay(**kw):
    return {
        'id': kw.get('id', 42),
        'uuid': kw.get('uuid', '5d12f6fd-a196-4bf0-ae4c-1f639a523a52'),
        'name': kw.get('name', 'bay1'),
        'discovery_url': kw.get('discovery_url', None),
        'ca_cert_ref': kw.get('ca_cert_ref', None),
        'magnum_cert_ref': kw.get('magnum_cert_ref', None),
        'project_id': kw.get('project_id', 'fake_project'),
        'user_id': kw.get('user_id', 'fake_user'),
        'baymodel_id': kw.get('baymodel_id',
                              'e74c40e0-d825-11e2-a28f-0800200c9a66'),
        'stack_id': kw.get('stack_id', '047c6319-7abd-4bd9-a033-8c6af0173cd0'),
        'status': kw.get('status', 'CREATE_IN_PROGRESS'),
        'status_reason': kw.get('status_reason', 'Completed successfully'),
        'bay_create_timeout': kw.get('bay_create_timeout', 0),
        'api_address': kw.get('api_address', '172.17.2.3'),
        'node_addresses': kw.get('node_addresses', ['172.17.2.4']),
        'node_count': kw.get('node_count', 3),
        'master_count': kw.get('master_count', 3),
        'master_addresses': kw.get('master_addresses', ['172.17.2.18']),
        'created_at': kw.get('created_at'),
        'updated_at': kw.get('updated_at'),
    }


def create_test_bay(**kw):
    """Create test bay entry in DB and return Bay DB object.

    Function to be used to create test Bay objects in the database.
    :param kw: kwargs with overriding values for bay's attributes.
    :returns: Test Bay DB object.
    """
    bay = get_test_bay(**kw)
    # Let DB generate ID if it isn't specified explicitly
    if 'id' not in kw:
        del bay['id']
    dbapi = db_api.get_instance()
    return dbapi.create_bay(bay)


def get_test_container(**kw):
    return {
        'id': kw.get('id', 42),
        'uuid': kw.get('uuid', 'ea8e2a25-2901-438d-8157-de7ffd68d051'),
        'name': kw.get('name', 'container1'),
        'project_id': kw.get('project_id', 'fake_project'),
        'user_id': kw.get('user_id', 'fake_user'),
        'image': kw.get('image', 'ubuntu'),
        'created_at': kw.get('created_at'),
        'updated_at': kw.get('updated_at'),
        'command': kw.get('command', 'fake_command'),
        'bay_uuid': kw.get('bay_uuid', 'fff114da-3bfa-4a0f-a123-c0dffad9718e'),
        'status': kw.get('state', 'Running'),
        'memory': kw.get('memory', '512m'),
        'environment': kw.get('environment', {'key1': 'val1', 'key2': 'val2'}),
    }


def create_test_container(**kw):
    """Create test container entry in DB and return Container DB object.

    Function to be used to create test Container objects in the database.
    :param kw: kwargs with overriding values for container's attributes.
    :returns: Test Container DB object.
    """
    container = get_test_container(**kw)
    # Let DB generate ID if it isn't specified explicitly
    if 'id' not in kw:
        del container['id']
    dbapi = db_api.get_instance()
    return dbapi.create_container(container)


def get_test_rc(**kw):
    return {
        'id': kw.get('id', 42),
        'uuid': kw.get('uuid', '10a47dd1-4874-4298-91cf-eff046dbdb8d'),
        'name': kw.get('name', 'replication_controller'),
        'project_id': kw.get('project_id', 'fake_project'),
        'user_id': kw.get('user_id', 'fake_user'),
        'images': kw.get('images', ['steak/for-dinner']),
        'bay_uuid': kw.get('bay_uuid', '5d12f6fd-a196-4bf0-ae4c-1f639a523a52'),
        'labels': kw.get('labels', {'name': 'foo'}),
        'replicas': kw.get('replicas', 3),
        'manifest_url': kw.get('file:///tmp/rc.yaml'),
        'created_at': kw.get('created_at'),
        'updated_at': kw.get('updated_at'),
    }


def create_test_rc(**kw):
    """Create test rc entry in DB and return ReplicationController DB object.

    Function to be used to create test ReplicationController objects in the
    database.
    :param kw: kwargs with overriding values for
               replication controller's attributes.
    :returns: Test ReplicationController DB object.
    """
    replication_controller = get_test_rc(**kw)
    # Let DB generate ID if it isn't specified explicitly
    if 'id' not in kw:
        del replication_controller['id']
    dbapi = db_api.get_instance()
    return dbapi.create_rc(replication_controller)


def get_test_x509keypair(**kw):
    return {
        'id': kw.get('id', 42),
        'uuid': kw.get('uuid', '72625085-c507-4410-9b28-cd7cf1fbf1ad'),
        'project_id': kw.get('project_id', 'fake_project'),
        'user_id': kw.get('user_id', 'fake_user'),
        'certificate': kw.get('certificate',
                              'certificate'),
        'private_key': kw.get('private_key', 'private_key'),
        'private_key_passphrase': kw.get('private_key_passphrase',
                                         'private_key_passphrase'),
        'intermediates': kw.get('intermediates', 'intermediates'),
        'created_at': kw.get('created_at'),
        'updated_at': kw.get('updated_at'),
    }


def create_test_x509keypair(**kw):
    """Create test x509keypair entry in DB and return X509KeyPair DB object.

    Function to be used to create test X509KeyPair objects in the database.
    :param kw: kwargs with overriding values for x509keypair's attributes.
    :returns: Test X509KeyPair DB object.
    """
    x509keypair = get_test_x509keypair(**kw)
    # Let DB generate ID if it isn't specified explicitly
    if 'id' not in kw:
        del x509keypair['id']
    dbapi = db_api.get_instance()
    return dbapi.create_x509keypair(x509keypair)


def get_test_magnum_service(**kw):
    return {
        'id': kw.get('', 13),
        'report_count': kw.get('report_count', 13),
        'host': kw.get('host', 'fakehost'),
        'binary': kw.get('binary', 'fake-bin'),
        'disabled': kw.get('disabled', False),
        'disabled_reason': kw.get('disabled_reason', 'fake-reason'),
        'forced_down': kw.get('forced_down', False),
        'last_seen_up': kw.get('last_seen_up'),
        'created_at': kw.get('created_at'),
        'updated_at': kw.get('updated_at'),
    }


def create_test_magnum_service(**kw):
    """Create test magnum_service entry in DB and return magnum_service DB object.

    :param kw: kwargs with overriding values for magnum_service's attributes.
    :returns: Test magnum_service DB object.
    """
    magnum_service = get_test_magnum_service(**kw)
    # Let DB generate ID if it isn't specified explicitly
    if 'id' not in kw:
        del magnum_service['id']
    dbapi = db_api.get_instance()
    return dbapi.create_magnum_service(magnum_service)


def get_test_quotas(**kw):
    return {
        'id': kw.get('', 18),
        'project_id': kw.get('project_id', 'fake_project'),
        'resource': kw.get('resource', 'fake_resource'),
        'hard_limit': kw.get('hard_limit', 10),
        'created_at': kw.get('created_at'),
        'updated_at': kw.get('updated_at'),
    }


def create_test_quotas(**kw):
    """Create test quotas entry in DB and return quotas DB object.

    :param kw: kwargs with overriding values for quota attributes.
    :returns: Test quotas DB object.
    """
    quotas = get_test_quotas(**kw)
    # Let DB generate ID if it isn't specified explicitly
    if 'id' not in kw:
        del quotas['id']
    dbapi = db_api.get_instance()
    return dbapi.create_quota(quotas)
