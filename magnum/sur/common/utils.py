import os
import yaml

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



