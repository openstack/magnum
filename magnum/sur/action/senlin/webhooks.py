'''
Created on Aug 16, 2015

'''

import json


class Webhook(object):
    base_url = '/webhooks'
    
    @classmethod
    def webhook_list(cls, sc):
        return sc.get(cls.base_url)
    
    @classmethod
    def __webhook_create(cls, sc, name, obj_type, obj_id, action, credential):
        args = {
            'webhook': {
                'name': name,
                'obj_type': obj_type,
                'obj_id': obj_id,
                'action': action,
                'credential': credential,
                'params': {}
            }
        }
        return sc.post(cls.base_url, data=json.dumps(args))
    
    @classmethod
    def cluster_webhook_create(cls, sc, name, obj_id, action, credential):
        return cls.__webhook_create(sc, name, 'cluster', obj_id,
                                    action, credential)
    
    @classmethod
    def node_webhook_create(cls, sc, name, obj_id, action, credential):
        return cls.__webhook_create(sc, name, 'node', obj_id,
                                    action, credential)
    
    @classmethod
    def policy_webhook_create(cls, sc, name, obj_id, action, credential):
        return cls.__webhook_create(sc, name, 'policy', obj_id,
                                    action, credential)
        
