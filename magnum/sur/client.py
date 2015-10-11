'''
Created on Aug 8, 2015

'''

from magnum.sur.common import utils
from magnum.sur.common import exception
from magnum.sur.common import client as sur_client

import keystoneclient.v3.client as ksclient


class SURClient(object):
    
    # default senlin args
    def __init__(self, host='localhost', port='8778', version='1',
                 name='senlin'):
        self._add_identity_args()
        
        if name in ['ceilometer']:
            self.endpoint = 'http://%s:%s/v%s' % (host, port, version)
        elif name in ['senlin']:
            self.endpoint = 'http://%s:%s/v%s/%s' % (
                host, port, version, self.identity_args['tenant_id'])

    def _add_identity_args(self):
        self.identity_args = {}
        self.identity_args['username'] = utils.get_env('OS_USERNAME')
        self.identity_args['password'] = utils.get_env('OS_PASSWORD')
        self.identity_args['user_id'] = utils.get_env('OS_USER_ID')
        self.identity_args['auth_url'] = utils.get_env('OS_AUTH_URL')
        self.identity_args['token'] = utils.get_env('OS_TOKEN', default=None)
        self.identity_args['project_id'] = utils.get_env('OS_PROJECT_ID')
        self.identity_args['project_name'] = utils.get_env('OS_PROJECT_NAME')
        self.identity_args['tenant_id'] = utils.get_env('OS_TENANT_ID')
        self.identity_args['tenant_name'] = utils.get_env('OS_TENANT_NAME')
        self.identity_args['domain_id'] = utils.get_env('OS_DOMAIN_ID')
        self.identity_args['domain_name'] = utils.get_env('OS_DOMAIN_NAME')
        self.identity_args['user_domain_id'] = utils.get_env(
            'OS_USER_DOMAIN_ID')
        self.identity_args['user_domain_name'] = utils.get_env(
            'OS_USER_DOMAIN_NAME')

        keystone = ksclient.Client(**self.identity_args)
        self.identity_args['token'] = keystone.auth_token
        self.identity_args['tenant_id'] = keystone.tenant_id

    def _check_identity_args(self, args):
        if not (args['username'] or args['token']) or not args['auth_url']:
            raise exception.IdentityArgsError

        if 'v3' in args['auth_url']:
            if args['username'] and not args['user_id']:
                if not (args['user_domain_id'] or args['user_domain_name']):
                    raise exception.IdentityArgsError

        if (args['username'] or args['user_id']) and not args['password']:
            raise exception.IdentityArgsError

        if not (args['project_id'] or args['project_name'] or
                args['tenant_id'] or args['tenant_name']):
            raise exception.IdentityArgsError

    def setup_client(self):
        # check if identity arguments are sufficient
        self._check_identity_args(self.identity_args)

        sc = sur_client.construct_sur_client(self.endpoint,
                                             **self.identity_args)
        return sc
