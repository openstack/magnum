'''
Created on Aug 9, 2015

'''

import json
from __builtin__ import classmethod


class Cluster(object):
    base_url = '/clusters'
    
    @classmethod
    def cluster_list(cls, sc):
        return sc.get(cls.base_url)
    
    @classmethod
    def cluster_create(cls, sc, name, profile_name):
        args = {
            "cluster": {
                'name': name,
                'profile_id': profile_name,
                'min_size': 0,
                'max_size': 0,
                'desired_capacity': 0,
                'parent': None,
                'metadata': {},
                'timeout': None
            }
        }
        return sc.post(cls.base_url, data=json.dumps(args))
    
    @classmethod
    def cluster_update(cls):
        pass
    
    @classmethod
    def cluster_delete(cls):
        pass
        
