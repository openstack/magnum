'''
Created on Aug 20, 2015

'''

import json


class Alarm(object):
    base_url = '/alarms'
    
    @classmethod
    def alarm_list(cls, cc):
        return cc.get(cls.base_url)
    
    @classmethod
    def alarm_threshold_create(cls, cc, **kwargs):
        args = {
            'name': kwargs['name'],
            'type': 'threshold',
            'threshold_rule': {
                'meter_name': kwargs['meter_name'],
                'threshold': kwargs['threshold']
            }
        }
        if 'state' in kwargs:
            args['state'] = kwargs['state']
        if 'severity' in kwargs:
            args['severity'] = kwargs['severity']
        if 'enabled' in kwargs:
            args['enabled'] = kwargs['enabled']
        if 'repeat_actions' in  kwargs:
            args['repeat_actions'] = False
        if 'alarm_actions' in kwargs:
            args['alarm_actions'] = kwargs['alarm_actions']
        if 'comparison_operator' in kwargs:
            args['threshold_rule']['comparison_operator'] = \
                kwargs['comparison_operator']
        if 'statistic' in kwargs:
            args['threshold_rule']['statistic'] = kwargs['statistic']
        
        return cc.post(cls.base_url, data=json.dumps(args))
    
    @classmethod
    def alarm_threshold_update(cls):
        pass
    
    @classmethod
    def alarm_delete(cls):
        pass
        
        