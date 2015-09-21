'''
Created on Aug 9, 2015

'''

import json

from magnum.sur.common import utils


class Profile(object):
    base_url = '/profiles'
    
    @classmethod
    def profile_list(cls, sc):
        return sc.get(cls.base_url)
    
    @classmethod
    def profile_create(cls, sc, name, profile_type, spec, permission):
        args = {         
            'profile': {
                'name': name,
                'permission': permission, 
                'spec': utils.get_spec_content(spec),
                'type': profile_type,
                'metadata': {}
            }
        }
        return sc.post(cls.base_url, data=json.dumps(args))
    
    @classmethod
    def profile_update(cls):
        pass
    
    @classmethod
    def profile_delete(cls):
        pass
