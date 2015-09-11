# Copyright 2013 - Red Hat, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Magnum base exception handling.

Includes decorator for re-raising Magnum-type exceptions.

"""

import functools
import sys
import uuid

from keystoneclient import exceptions as keystone_exceptions
from oslo_config import cfg
from oslo_log import log as logging
from oslo_utils import excutils
import pecan
import six
import wsme

from magnum.common import safe_utils
from magnum.i18n import _
from magnum.i18n import _LE


LOG = logging.getLogger(__name__)

CONF = cfg.CONF

try:
    CONF.import_opt('fatal_exception_format_errors',
                    'oslo_versionedobjects.exception')
except cfg.NoSuchOptError as e:
    # Note:work around for magnum run against master branch
    # in devstack gate job, as magnum not branched yet
    # verisonobjects kilo/master different version can
    # cause issue here. As it changed import group. So
    # add here before branch to prevent gate failure.
    # Bug: #1447873
    CONF.import_opt('fatal_exception_format_errors',
                    'oslo_versionedobjects.exception',
                    group='oslo_versionedobjects')


def wrap_exception(notifier=None, event_type=None):
    """This decorator wraps a method to catch any exceptions.

    It logs the exception as well as optionally sending
    it to the notification system.
    """
    def inner(f):
        def wrapped(self, context, *args, **kw):
            # Don't store self or context in the payload, it now seems to
            # contain confidential information.
            try:
                return f(self, context, *args, **kw)
            except Exception as e:
                with excutils.save_and_reraise_exception():
                    if notifier:
                        call_dict = safe_utils.getcallargs(f, context,
                                                           *args, **kw)
                        payload = dict(exception=e,
                                       private=dict(args=call_dict)
                                       )

                        temp_type = event_type
                        if not temp_type:
                            # If f has multiple decorators, they must use
                            # functools.wraps to ensure the name is
                            # propagated.
                            temp_type = f.__name__

                        notifier.error(context, temp_type, payload)

        return functools.wraps(f)(wrapped)
    return inner


OBFUSCATED_MSG = _('Your request could not be handled '
                   'because of a problem in the server. '
                   'Error Correlation id is: %s')


def wrap_controller_exception(func, func_server_error, func_client_error):
    """This decorator wraps controllers methods to handle exceptions:

    - if an unhandled Exception or a MagnumException with an error code >=500
    is catched, raise a http 5xx ClientSideError and correlates it with a log
    message

    - if a MagnumException is catched and its error code is <500, raise a http
    4xx and logs the excp in debug mode

    """
    @functools.wraps(func)
    def wrapped(*args, **kw):
        try:
            return func(*args, **kw)
        except Exception as excp:
            if isinstance(excp, MagnumException):
                http_error_code = excp.code
            else:
                http_error_code = 500

            if http_error_code >= 500:
                # log the error message with its associated
                # correlation id
                log_correlation_id = str(uuid.uuid4())
                LOG.error(_LE("%(correlation_id)s:%(excp)s") %
                          {'correlation_id': log_correlation_id,
                           'excp': str(excp)})
                # raise a client error with an obfuscated message
                func_server_error(log_correlation_id, http_error_code)
            else:
                # raise a client error the original message
                LOG.debug(excp)
                func_client_error(excp, http_error_code)
    return wrapped


def wrap_wsme_controller_exception(func):
    """This decorator wraps wsme controllers to handle exceptions."""
    def _func_server_error(log_correlation_id, status_code):
        raise wsme.exc.ClientSideError(
            six.text_type(OBFUSCATED_MSG % log_correlation_id), status_code)

    def _func_client_error(excp, status_code):
        raise wsme.exc.ClientSideError(six.text_type(excp), status_code)

    return wrap_controller_exception(func,
                                     _func_server_error,
                                     _func_client_error)


def wrap_pecan_controller_exception(func):
    """This decorator wraps pecan controllers to handle exceptions."""
    def _func_server_error(log_correlation_id, status_code):
        pecan.response.status = status_code
        pecan.response.text = six.text_type(OBFUSCATED_MSG %
                                            log_correlation_id)

    def _func_client_error(excp, status_code):
        pecan.response.status = status_code
        pecan.response.text = six.text_type(excp)
        pecan.response.content_type = None

    return wrap_controller_exception(func,
                                     _func_server_error,
                                     _func_client_error)


def wrap_keystone_exception(func):
    """Wrap keystone exceptions and throw Magnum specific exceptions."""
    @functools.wraps(func)
    def wrapped(*args, **kw):
        try:
            return func(*args, **kw)
        except keystone_exceptions.AuthorizationFailure:
            raise AuthorizationFailure(
                client=func.__name__, message="reason: %s" % sys.exc_info()[1])
        except keystone_exceptions.ClientException:
            raise AuthorizationFailure(
                client=func.__name__,
                message="unexpected keystone client error occurred: %s"
                        % sys.exc_info()[1])
    return wrapped


class MagnumException(Exception):
    """Base Magnum Exception

    To correctly use this class, inherit from it and define
    a 'message' property. That message will get printf'd
    with the keyword arguments provided to the constructor.

    """
    message = _("An unknown exception occurred.")
    code = 500

    def __init__(self, message=None, **kwargs):
        self.kwargs = kwargs

        if 'code' not in self.kwargs:
            try:
                self.kwargs['code'] = self.code
            except AttributeError:
                pass

        if message:
            self.message = message

        try:
            self.message = self.message % kwargs
        except Exception as e:
            # kwargs doesn't match a variable in the message
            # log the issue and the kwargs
            LOG.exception(_LE('Exception in string format operation'))
            for name, value in kwargs.items():
                LOG.error(_LE("%(name)s: %(value)s") %
                          {'name': name, 'value': value})
            try:
                if CONF.fatal_exception_format_errors:
                    raise e
            except cfg.NoSuchOptError:
                # Note: work around for Bug: #1447873
                if CONF.oslo_versionedobjects.fatal_exception_format_errors:
                    raise e

        super(MagnumException, self).__init__(self.message)

    def __str__(self):
        if six.PY3:
            return self.message
        return self.message.encode('utf-8')

    def __unicode__(self):
        return self.message

    def format_message(self):
        if self.__class__.__name__.endswith('_Remote'):
            return self.args[0]
        else:
            return six.text_type(self)


class ObjectNotFound(MagnumException):
    message = _("The %(name)s %(id)s could not be found.")


class ObjectNotUnique(MagnumException):
    message = _("The %(name)s already exists.")


class ResourceNotFound(ObjectNotFound):
    message = _("The %(name)s resource %(id)s could not be found.")
    code = 404


class ResourceExists(ObjectNotUnique):
    message = _("The %(name)s resource already exists.")
    code = 409


class AuthorizationFailure(MagnumException):
    message = _("%(client)s connection failed. %(message)s")


class UnsupportedObjectError(MagnumException):
    message = _('Unsupported object type %(objtype)s')


class IncompatibleObjectVersion(MagnumException):
    message = _('Version %(objver)s of %(objname)s is not supported')


class OrphanedObjectError(MagnumException):
    message = _('Cannot call %(method)s on orphaned %(objtype)s object')


class Invalid(MagnumException):
    message = _("Unacceptable parameters.")
    code = 400


class InvalidUUID(Invalid):
    message = _("Expected a uuid but received %(uuid)s.")


class InvalidName(Invalid):
    message = _("Expected a name but received %(uuid)s.")


class InvalidDiscoveryURL(Invalid):
    message = _("Received invalid discovery URL '%(discovery_url)s' for "
                "discovery endpoint '%(discovery_endpoint)s'.")


class InvalidUuidOrName(Invalid):
    message = _("Expected a name or uuid but received %(uuid)s.")


class InvalidIdentity(Invalid):
    message = _("Expected an uuid or int but received %(identity)s.")


class HTTPNotFound(ResourceNotFound):
    pass


class Conflict(MagnumException):
    message = _('Conflict.')
    code = 409


class InvalidState(Conflict):
    message = _("Invalid resource state.")


# Cannot be templated as the error syntax varies.
# msg needs to be constructed when raised.
class InvalidParameterValue(Invalid):
    message = _("%(err)s")


class InstanceAssociated(Conflict):
    message = _("Instance %(instance_uuid)s is already associated with a node,"
                " it cannot be associated with this other node %(node)s")


class InstanceNotFound(ResourceNotFound):
    message = _("Instance %(instance)s could not be found.")


class PatchError(Invalid):
    message = _("Couldn't apply patch '%(patch)s'. Reason: %(reason)s")


class NotAuthorized(MagnumException):
    message = _("Not authorized.")
    code = 403


class NotAcceptable(MagnumException):
    # TODO(yuntongjin): We need to set response headers
    # in the API for this exception
    message = _("Request not acceptable.")
    code = 406


class InvalidMAC(Invalid):
    message = _("Expected a MAC address but received %(mac)s.")


class ConfigInvalid(MagnumException):
    message = _("Invalid configuration file. %(error_msg)s")


class NodeAlreadyExists(Conflict):
    message = _("A node with UUID %(uuid)s already exists.")


class NodeNotFound(ResourceNotFound):
    message = _("Node %(node)s could not be found.")


class NodeAssociated(InvalidState):
    message = _("Node %(node)s is associated with instance %(instance)s.")


class SSHConnectFailed(MagnumException):
    message = _("Failed to establish SSH connection to host %(host)s.")


class FileSystemNotSupported(MagnumException):
    message = _("Failed to create a file system. "
                "File system %(fs)s is not supported.")


class BayModelNotFound(ResourceNotFound):
    message = _("Baymodel %(baymodel)s could not be found.")


class BayModelAlreadyExists(Conflict):
    message = _("A baymodel with UUID %(uuid)s already exists.")


class BayModelReferenced(Invalid):
    message = _("Baymodel %(baymodel)s is referenced by one or multiple bays.")


class BayNotFound(ResourceNotFound):
    message = _("Bay %(bay)s could not be found.")


class BayAlreadyExists(Conflict):
    message = _("A node with UUID %(uuid)s already exists.")


class ContainerNotFound(ResourceNotFound):
    message = _("Container %(container)s could not be found.")


class ContainerAlreadyExists(Conflict):
    message = _("A container with UUID %(uuid)s already exists.")


class PodNotFound(ResourceNotFound):
    message = _("Pod %(pod)s could not be found.")


class PodAlreadyExists(Conflict):
    message = _("A node with UUID %(uuid)s already exists.")


class ReplicationControllerNotFound(ResourceNotFound):
    message = _("ReplicationController %(rc)s could not be found.")


class ReplicationControllerAlreadyExists(Conflict):
    message = _("A ReplicationController with UUID %(uuid)s already exists.")


class ServiceNotFound(ResourceNotFound):
    message = _("Service %(service)s could not be found.")


class ServiceAlreadyExists(Conflict):
    message = _("A node with UUID %(uuid)s already exists.")


class ContainerException(Exception):
    pass


class NotSupported(MagnumException):
    message = _("%(operation)s is not supported.")
    code = 400


class BayTypeNotSupported(MagnumException):
    message = _("Bay type (%(server_type)s, %(os)s, %(coe)s)"
                " not supported.")


class BayTypeNotEnabled(MagnumException):
    message = _("Bay type (%(server_type)s, %(os)s, %(coe)s)"
                " not enabled.")


class RequiredParameterNotProvided(MagnumException):
    message = _("Required parameter %(heat_param)s not provided.")


class Urllib2InvalidScheme(MagnumException):
    message = _("The urllib2 URL %(url)s has an invalid scheme.")


class OperationInProgress(Invalid):
    message = _("Bay %(bay_name)s already has an operation in progress.")


class ImageNotFound(ResourceNotFound):
    message = _("Image %(image_id)s could not be found.")


class ImageNotAuthorized(MagnumException):
    message = _("Not authorized for image %(image_id)s.")


class OSDistroFieldNotFound(ResourceNotFound):
    message = _("Image %(image_id)s doesn't contain os_distro field.")


class KubernetesAPIFailed(MagnumException):
    def __init__(self, message=None, **kwargs):
        self.__class__.code = kwargs.get('code')
        super(KubernetesAPIFailed, self).__init__(message, **kwargs)


class X509KeyPairNotFound(ResourceNotFound):
    message = _("A key pair %(keypair)s could not be found.")


class X509KeyPairAlreadyExists(Conflict):
    message = _("A key pair with UUID %(uuid)s already exists.")


class CertificateStorageException(MagnumException):
    message = _("Could not store certificate: %(msg)s")


class CertificateValidationError(Invalid):
    message = _("Extension '%(extension)s' not allowed")


class KeyPairNotFound(ResourceNotFound):
    message = _("Unable to find keypair %(keypair)s.")
