'''
Created on Aug 6, 2015

'''

import os
import yaml

from heatclient.common import template_utils

from magnum.sur.common import exception


def get_env(env_name, default=''):
    value = os.environ.get(env_name)
    if value:
        return value
    return default


def get_spec_content(filename):
    with open(filename, 'r') as f:
        try:
            data = yaml.load(f)
        except Exception as ex:
            raise exception.InvalidYAMLFileError

    return data


def url_join(*args):
    return '/'.join([str(e).strip('/') for e in args])


def process_spec(spec):
    template_file = spec.get('template', None)
    
    tpl_files, template = template_utils.get_template_contents(
        template_file=template_file)

    env_files, env = template_utils.process_multiple_environments_and_files(
        env_paths=spec.get('environment', None))

    new_spec = {
        'disable_rollback': spec.get('disable_rollback', True),
        'context':  spec.get('context', {}),
        'parameters': spec.get('parameters', {}),
        'timeout': spec.get('timeout', 60),
        'template': template,
        'files': dict(list(tpl_files.items()) + list(env_files.items())),
        'environment': env
    }

    return new_spec
