'''
Created on Aug 9, 2015

'''

import json
from __builtin__ import classmethod


class Cluster(object):
    base_url = '/clusters'
    action_url = '/clusters/%(cluster_id)s/action'

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
                'max_size': 10,
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
    
    @classmethod
    def cluster_policy_attach(cls, sc, cluster_name, policy_name, enabled=True,
                              priority=50, level=50, cooldown=0):
        url = cls.action_url % {'cluster_id': cluster_name}
        args = {
            'policy_attach': {
                'policy_id': policy_name,
                'priority': priority,
                'level': level,
                'cooldown': cooldown,
                'enabled': enabled
            }
        }
        return sc.put(url, data=json.dumps(args))
    
    @classmethod
    def cluster_policy_detach(cls, sc, cluster_name, policy_name):
        url = cls.action_url % {'cluster_id': cluster_name}
        args = {
            'policy_detach': {
                'policy_id': policy_name
            }
        }
        return sc.put(url, data=json.dumps(args))
    
    @classmethod
    def cluster_scale_out(cls, sc, cluster_name, count=None):
        url = cls.action_url % {'cluster_id': cluster_name}
        args = {
            'scale_out': {
                'count': count
            }
        }
        return sc.put(url, data=json.dumps(args))
    
    @classmethod
    def cluster_scale_in(cls, sc, cluster_name, count=None):
        url = cls.action_url % {'cluster_id': cluster_name}
        args = {
            'scale_in': {
                'count': count
            }
        }
        return sc.put(url, data=json.dumps(args))

