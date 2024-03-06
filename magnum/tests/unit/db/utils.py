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

from oslo_utils import uuidutils

from magnum.db import api as db_api


def get_test_cluster_template(**kw):
    return {
        'id': kw.get('id', 32),
        'project_id': kw.get('project_id', 'fake_project'),
        'user_id': kw.get('user_id', 'fake_user'),
        'uuid': kw.get('uuid', 'e74c40e0-d825-11e2-a28f-0800200c9a66'),
        'name': kw.get('name', 'clustermodel1'),
        'image_id': kw.get('image_id', 'ubuntu'),
        'flavor_id': kw.get('flavor_id', 'm1.small'),
        'master_flavor_id': kw.get('master_flavor_id', 'm1.small'),
        'keypair_id': kw.get('keypair_id', 'keypair1'),
        'external_network_id': kw.get('external_network_id',
                                      'd1f02cfb-d27f-4068-9332-84d907cb0e2e'),
        'fixed_network': kw.get('fixed_network', 'private'),
        'fixed_subnet': kw.get('fixed_network', 'private-subnet'),
        'network_driver': kw.get('network_driver'),
        'volume_driver': kw.get('volume_driver'),
        'dns_nameserver': kw.get('dns_nameserver', '8.8.1.1'),
        'apiserver_port': kw.get('apiserver_port', 8080),
        'docker_volume_size': kw.get('docker_volume_size', 20),
        'docker_storage_driver': kw.get('docker_storage_driver',
                                        'devicemapper'),
        'cluster_distro': kw.get('cluster_distro', 'fedora-coreos'),
        'coe': kw.get('coe', 'kubernetes'),
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
        'master_lb_enabled': kw.get('master_lb_enabled', True),
        'floating_ip_enabled': kw.get('floating_ip_enabled', True),
        'hidden': kw.get('hidden', False),
        'tags': kw.get('tags', ""),
        'driver': kw.get('driver', ""),
    }


def create_test_cluster_template(**kw):
    """Create and return test ClusterTemplate DB object.

    Function to be used to create test ClusterTemplate objects in the database.
    :param kw: kwargs with overriding values for ClusterTemplate's attributes.
    :returns: Test ClusterTemplate DB object.
    """
    cluster_template = get_test_cluster_template(**kw)
    # Let DB generate ID if it isn't specified explicitly
    if 'id' not in kw:
        del cluster_template['id']
    dbapi = db_api.get_instance()
    return dbapi.create_cluster_template(cluster_template)


def get_test_cluster(**kw):
    attrs = {
        'id': kw.get('id', 42),
        'uuid': kw.get('uuid', '5d12f6fd-a196-4bf0-ae4c-1f639a523a52'),
        'name': kw.get('name', 'cluster1'),
        'discovery_url': kw.get('discovery_url', None),
        'ca_cert_ref': kw.get('ca_cert_ref', None),
        'magnum_cert_ref': kw.get('magnum_cert_ref', None),
        'project_id': kw.get('project_id', 'fake_project'),
        'user_id': kw.get('user_id', 'fake_user'),
        'cluster_template_id': kw.get('cluster_template_id',
                                      'e74c40e0-d825-11e2-a28f-0800200c9a66'),
        'stack_id': kw.get('stack_id', '047c6319-7abd-4bd9-a033-8c6af0173cd0'),
        'status': kw.get('status', 'CREATE_IN_PROGRESS'),
        'status_reason': kw.get('status_reason', 'Completed successfully'),
        'create_timeout': kw.get('create_timeout', 60),
        'api_address': kw.get('api_address', '172.17.2.3'),
        'created_at': kw.get('created_at'),
        'updated_at': kw.get('updated_at'),
        'docker_volume_size': kw.get('docker_volume_size'),
        'labels': kw.get('labels'),
        'master_flavor_id': kw.get('master_flavor_id', None),
        'flavor_id': kw.get('flavor_id', None),
        'fixed_network': kw.get('fixed_network', None),
        'fixed_subnet': kw.get('fixed_subnet', None),
        'floating_ip_enabled': kw.get('floating_ip_enabled', True),
        'master_lb_enabled': kw.get('master_lb_enabled', True),
        'etcd_ca_cert_ref': kw.get('etcd_ca_cert_ref', None),
        'front_proxy_ca_cert_ref': kw.get('front_proxy_ca_cert_ref', None)
    }

    if kw.pop('for_api_use', False):
        attrs.update({
            'node_addresses': kw.get('node_addresses', ['172.17.2.4']),
            'node_count': kw.get('node_count', 3),
            'master_count': kw.get('master_count', 3),
            'master_addresses': kw.get('master_addresses', ['172.17.2.18'])
        })
    # Only add Keystone trusts related attributes on demand since they may
    # break other tests.
    for attr in ['trustee_username', 'trustee_password', 'trust_id']:
        if attr in kw:
            attrs[attr] = kw[attr]
    # Required only in PeriodicTestCase, may break other tests
    for attr in ['keypair', 'health_status', 'health_status_reason']:
        if attr in kw:
            attrs[attr] = kw[attr]

    return attrs


def create_test_cluster(**kw):
    """Create test cluster entry in DB and return Cluster DB object.

    Function to be used to create test Cluster objects in the database.
    :param kw: kwargs with overriding values for cluster's attributes.
    :returns: Test Cluster DB object.
    """
    cluster = get_test_cluster(**kw)
    # Let DB generate ID if it isn't specified explicitly
    if 'id' not in kw:
        del cluster['id']
    dbapi = db_api.get_instance()
    return dbapi.create_cluster(cluster)


def get_test_quota(**kw):
    attrs = {
        'id': kw.get('id', 42),
        'project_id': kw.get('project_id', 'fake_project'),
        'resource': kw.get('resource', 'Cluster'),
        'hard_limit': kw.get('hard_limit', 10)
    }

    return attrs


def create_test_quota(**kw):
    """Create test quota entry in DB and return Quota DB object.

    Function to be used to create test Quota objects in the database.
    :param kw: kwargs with overriding values for quota's attributes.
    :returns: Test Quota DB object.
    """
    quota = get_test_quota(**kw)
    # Let DB generate ID if it isn't specified explicitly
    if 'id' not in kw:
        del quota['id']
    dbapi = db_api.get_instance()
    return dbapi.create_quota(quota)


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
        'resource': kw.get('resource', 'Cluster'),
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


def get_test_federation(**kw):
    return {
        'id': kw.get('id', 42),
        'uuid': kw.get('uuid', '60d6dbdc-9951-4cee-b020-55d3e15a749b'),
        'name': kw.get('name', 'fake-name'),
        'project_id': kw.get('project_id', 'fake_project'),
        'hostcluster_id': kw.get('hostcluster_id', 'fake_master'),
        'member_ids': kw.get('member_ids', ['fake_member1', 'fake_member2']),
        'properties': kw.get('properties', {'dns-zone': 'example.com.'}),
        'status': kw.get('status', 'CREATE_IN_PROGRESS'),
        'status_reason': kw.get('status_reason', 'Completed successfully.'),
        'created_at': kw.get('created_at'),
        'updated_at': kw.get('updated_at')
    }


def create_test_federation(**kw):
    """Create test federation entry in DB and return federation DB object.

    :param kw: kwargs with overriding values for federation attributes.
    :return: Test quotas DB object.
    """
    federation = get_test_federation(**kw)
    # Let DB generate ID if it isn't specified explicitly
    if 'id' not in kw:
        del federation['id']
    dbapi = db_api.get_instance()
    return dbapi.create_federation(federation)


def get_test_nodegroup(**kw):
    return {
        'id': kw.get('id', 12),
        'uuid': kw.get('uuid', '483203a3-dbee-4a9c-9d65-9820512f4df8'),
        'name': kw.get('name', 'nodegroup1'),
        'cluster_id': kw.get('cluster_id',
                             '5d12f6fd-a196-4bf0-ae4c-1f639a523a52'),
        'project_id': kw.get('project_id', 'fake_project'),
        'docker_volume_size': kw.get('docker_volume_size'),
        'labels': kw.get('labels'),
        'flavor_id': kw.get('flavor_id', None),
        'image_id': kw.get('image_id', None),
        'node_addresses': kw.get('node_addresses', ['172.17.2.4']),
        'node_count': kw.get('node_count', 3),
        'role': kw.get('role', 'worker'),
        'max_node_count': kw.get('max_node_count', None),
        'min_node_count': kw.get('min_node_count', 1),
        'is_default': kw.get('is_default', True),
        'created_at': kw.get('created_at'),
        'updated_at': kw.get('updated_at'),
        'status': kw.get('status', 'CREATE_COMPLETE'),
        'status_reason': kw.get('status_reason', 'Completed successfully'),
        'version': kw.get('version', '1'),
        'stack_id': kw.get('stack_id', '047c6319-7abd-fake-a033-8c6af0173cd0'),
    }


def create_test_nodegroup(**kw):
    """Create test nodegroup entry in DB and return federation DB object.

    :param kw: kwargs with overriding values for nodegroup attributes.
    :return: Test nodegroup DB object.
    """
    nodegroup = get_test_nodegroup(**kw)
    # Let DB generate ID if it isn't specified explicitly
    if 'id' in nodegroup:
        del nodegroup['id']
    dbapi = db_api.get_instance()
    return dbapi.create_nodegroup(nodegroup)


def get_nodegroups_for_cluster(**kw):
    # get workers nodegroup
    worker = get_test_nodegroup(
        role='worker',
        name=kw.get('worker_name', 'test-worker'),
        uuid=kw.get('worker_uuid', uuidutils.generate_uuid()),
        cluster_id=kw.get('cluster_id',
                          '5d12f6fd-a196-4bf0-ae4c-1f639a523a52'),
        project_id=kw.get('project_id', 'fake_project'),
        node_addresses=kw.get('node_addresses', ['172.17.2.4']),
        node_count=kw.get('node_count', 3),
        status=kw.get('worker_status', 'CREATE_COMPLETE'),
        status_reason=kw.get('worker_reason', 'Completed successfully'),
        image_id=kw.get('image_id', 'test_image')
    )

    # get masters nodegroup
    master = get_test_nodegroup(
        role='master',
        name=kw.get('master_name', 'test-master'),
        uuid=kw.get('master_uuid', uuidutils.generate_uuid()),
        cluster_id=kw.get('cluster_id',
                          '5d12f6fd-a196-4bf0-ae4c-1f639a523a52'),
        project_id=kw.get('project_id', 'fake_project'),
        node_addresses=kw.get('master_addresses', ['172.17.2.18']),
        node_count=kw.get('master_count', 3),
        status=kw.get('master_status', 'CREATE_COMPLETE'),
        status_reason=kw.get('master_reason', 'Completed successfully'),
        image_id=kw.get('image_id', 'test_image')
    )
    return {'master': master, 'worker': worker}


def create_nodegroups_for_cluster(**kw):
    nodegroups = get_nodegroups_for_cluster(**kw)
    # Create workers nodegroup
    worker = nodegroups['worker']
    del worker['id']
    create_test_nodegroup(**worker)

    # Create masters nodegroup
    master = nodegroups['master']
    del master['id']
    create_test_nodegroup(**master)
