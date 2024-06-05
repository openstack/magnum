# Copyright (c) 2015 OpenStack Foundation
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

"""Policy Engine For magnum."""

import decorator
from oslo_config import cfg
from oslo_policy import opts
from oslo_policy import policy
from oslo_utils import importutils
import pecan

from magnum.common import clients
from magnum.common import exception
from magnum.common import policies


_ENFORCER = None
CONF = cfg.CONF

# TODO(gmann): Remove setting the default value of config policy_file
# once oslo_policy change the default value to 'policy.yaml'.
# https://github.com/openstack/oslo.policy/blob/a626ad12fe5a3abd49d70e3e5b95589d279ab578/oslo_policy/opts.py#L49
DEFAULT_POLICY_FILE = 'policy.yaml'
opts.set_defaults(CONF, DEFAULT_POLICY_FILE)


# we can get a policy enforcer by this init.
# oslo policy support change policy rule dynamically.
# at present, policy.enforce will reload the policy rules when it checks
# the policy files have been touched.
def init(policy_file=None, rules=None,
         default_rule=None, use_conf=True, overwrite=True):
    """Init an Enforcer class.

        :param policy_file: Custom policy file to use, if none is
                            specified, ``conf.policy_file`` will be
                            used.
        :param rules: Default dictionary / Rules to use. It will be
                      considered just in the first instantiation. If
                      :meth:`load_rules` with ``force_reload=True``,
                      :meth:`clear` or :meth:`set_rules` with
                      ``overwrite=True`` is called this will be overwritten.
        :param default_rule: Default rule to use, conf.default_rule will
                             be used if none is specified.
        :param use_conf: Whether to load rules from cache or config file.
        :param overwrite: Whether to overwrite existing rules when reload rules
                          from config file.
    """
    global _ENFORCER
    if not _ENFORCER:
        # http://docs.openstack.org/developer/oslo.policy/usage.html
        _ENFORCER = policy.Enforcer(CONF,
                                    policy_file=policy_file,
                                    rules=rules,
                                    default_rule=default_rule,
                                    use_conf=use_conf,
                                    overwrite=overwrite)
        _ENFORCER.register_defaults(policies.list_rules())

    return _ENFORCER


def enforce(context, rule=None, target=None,
            do_raise=True, exc=None, *args, **kwargs):

    """Checks authorization of a rule against the target and credentials.

        :param dict context: As much information about the user performing the
                             action as possible.
        :param rule: The rule to evaluate.
        :param dict target: As much information about the object being operated
                            on as possible.
        :param do_raise: Whether to raise an exception or not if check
                         fails.
        :param exc: Class of the exception to raise if the check fails.
                    Any remaining arguments passed to :meth:`enforce` (both
                    positional and keyword arguments) will be passed to
                    the exception class. If not specified,
                    :class:`PolicyNotAuthorized` will be used.

        :return: ``False`` if the policy does not allow the action and `exc` is
                 not provided; otherwise, returns a value that evaluates to
                 ``True``.  Note: for rules using the "case" expression, this
                 ``True`` value will be the specified string from the
                 expression.
    """
    enforcer = init()
    credentials = context.to_dict()
    if not exc:
        exc = exception.PolicyNotAuthorized
    if target is None:
        target = {'project_id': context.project_id,
                  'user_id': context.user_id}
    add_policy_attributes(target)
    return enforcer.enforce(rule, target, credentials,
                            do_raise=do_raise, exc=exc, *args, **kwargs)


def add_policy_attributes(target):
    """Adds extra information for policy enforcement to raw target object"""
    context = importutils.import_module('magnum.common.context')
    admin_context = context.make_admin_context()
    admin_osc = clients.OpenStackClients(admin_context)
    trustee_domain_id = admin_osc.keystone().trustee_domain_id
    target['trustee_domain_id'] = trustee_domain_id
    return target


def get_enforcer():
    # This method is used by oslopolicy CLI scripts in order to generate policy
    # files from overrides on disk and defaults in code.
    cfg.CONF([], project='magnum')
    init()
    return _ENFORCER


def check_is_admin(context):
    """Whether or not user is admin according to policy setting.

    """
    init()
    target = {}
    credentials = context.to_dict()
    return _ENFORCER.enforce('context_is_admin', target, credentials)


def enforce_wsgi(api_name, act=None):
    """This is a decorator to simplify wsgi action policy rule check.

        :param api_name: The collection name to be evaluate.
        :param act: The function name of wsgi action.

       example:
           from magnum.common import policy
           class ClustersController(rest.RestController):
               ....
               @policy.enforce_wsgi("cluster", "delete")
               @wsme_pecan.wsexpose(None, types.uuid_or_name, status_code=204)
               def delete(self, cluster_ident):
                   ...
    """
    @decorator.decorator
    def wrapper(fn, *args, **kwargs):
        action = "%s:%s" % (api_name, (act or fn.__name__))
        enforce(pecan.request.context, action,
                exc=exception.PolicyNotAuthorized, action=action)
        return fn(*args, **kwargs)
    return wrapper
