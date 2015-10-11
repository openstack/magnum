'''
Created on Aug 16, 2015

'''

import json

from magnum.sur.common import utils


class Policy(object):
    base_url = '/policies'
    
    @classmethod
    def policy_list(cls, sc):
        return sc.get(cls.base_url)
    
    @classmethod
    def policy_create(cls, sc, name, policy_type, spec, level=0, cooldown=0):
        args = {
            'policy': {
                'name': name,
                'type': policy_type,
                'level': level,
                'cooldown': cooldown,
                'spec': utils.get_spec_content(spec)
            }
        }
        return sc.post(cls.base_url, data=json.dumps(args))
    
    @classmethod
    def policy_update(cls):
        pass
    
    @classmethod
    def policy_delete(cls):
        pass
    

class LoadBalancingPolicy(Policy):

    @classmethod
    def policy_create(cls, sc, name, spec, level=0, cooldown=0):
        super(LoadBalancingPolicy, cls).policy_create(sc, name,
                                                      'LoadBalancingPolicy',
                                                      spec, level, cooldown)


class ScalingInPolicy(Policy):

    @classmethod
    def policy_create(cls, sc, name, spec, level=0, cooldown=0):
        super(ScalingInPolicy, cls).policy_create(sc, name,
                                                  'ScalingInPolicy',
                                                  spec, level, cooldown)


class ScalingOutPolicy(Policy):

    @classmethod
    def policy_create(cls, sc, name, spec, level=0, cooldown=0):
        super(ScalingOutPolicy, cls).policy_create(sc, name,
                                                   'ScalingOutPolicy',
                                                   spec, level, cooldown)
