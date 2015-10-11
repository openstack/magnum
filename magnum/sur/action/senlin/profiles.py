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
        spec = utils.get_spec_content(spec)
        type_name = spec.get('type', None)
        type_version = spec.get('version', None)
        properties = spec.get('properties', None)
        args = {
            'profile': {
                'name': name,
                'permission': permission,
                'spec': {
		    'version': type_version,
                    'type': type_name,
                    'properties': utils.process_spec(properties)
                },
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
