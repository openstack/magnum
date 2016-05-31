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
import json
import sys

from keystoneclient import exceptions as keystone_exceptions
from oslo_config import cfg
from oslo_log import log as logging
import six

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

        if 'code' not in self.kwargs and hasattr(self, 'code'):
            self.kwargs['code'] = self.code

        if message:
            self.message = message

        try:
            self.message = self.message % kwargs
        except Exception as e:
            # kwargs doesn't match a variable in the message
            # log the issue and the kwargs
            LOG.exception(_LE('Exception in string format operation, '
                              'kwargs: %s') % kwargs)
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


class ResourceNotFound(ObjectNotFound):
    message = _("The %(name)s resource %(id)s could not be found.")
    code = 404


class AuthorizationFailure(MagnumException):
    message = _("%(client)s connection failed. %(message)s")


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


class GetDiscoveryUrlFailed(MagnumException):
    message = _("Failed to get discovery url from '%(discovery_endpoint)s'.")


class InvalidIdentity(Invalid):
    message = _("Expected an uuid or int but received %(identity)s.")


class InvalidCsr(Invalid):
    message = _("Received invalid csr %(csr)s.")


class HTTPNotFound(ResourceNotFound):
    pass


class Conflict(MagnumException):
    message = _('Conflict.')
    code = 409


# Cannot be templated as the error syntax varies.
# msg needs to be constructed when raised.
class InvalidParameterValue(Invalid):
    message = _("%(err)s")


class PatchError(Invalid):
    message = _("Couldn't apply patch '%(patch)s'. Reason: %(reason)s")


class NotAuthorized(MagnumException):
    message = _("Not authorized.")
    code = 403


class PolicyNotAuthorized(NotAuthorized):
    message = _("Policy doesn't allow %(action)s to be performed.")


class InvalidMAC(Invalid):
    message = _("Expected a MAC address but received %(mac)s.")


class ConfigInvalid(MagnumException):
    message = _("Invalid configuration file. %(error_msg)s")


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


class BaymodelPublishDenied(NotAuthorized):
    message = _("Not authorized to set public flag for baymodel.")


class BayNotFound(ResourceNotFound):
    message = _("Bay %(bay)s could not be found.")


class BayAlreadyExists(Conflict):
    message = _("A bay with UUID %(uuid)s already exists.")


class ContainerNotFound(ResourceNotFound):
    message = _("Container %(container)s could not be found.")


class ContainerAlreadyExists(Conflict):
    message = _("A container with UUID %(uuid)s already exists.")


class PodNotFound(ResourceNotFound):
    message = _("Pod %(pod)s could not be found.")


class PodAlreadyExists(Conflict):
    message = _("A pod with UUID %(uuid)s already exists.")


class PodListNotFound(ResourceNotFound):
    message = _("Pod list could not be found for Bay %(bay_uuid)s.")


class PodCreationFailed(Invalid):
    message = _("Pod creation failed in Bay %(bay_uuid)s.")


class ReplicationControllerNotFound(ResourceNotFound):
    message = _("ReplicationController %(rc)s could not be found.")


class ReplicationControllerAlreadyExists(Conflict):
    message = _("A ReplicationController with UUID %(uuid)s already exists.")


class ReplicationControllerListNotFound(ResourceNotFound):
    message = _("ReplicationController list could not be found"
                " for Bay %(bay_uuid)s.")


class ReplicationControllerCreationFailed(Invalid):
    message = _("ReplicationController creation failed"
                " for Bay %(bay_uuid)s.")


class ServiceNotFound(ResourceNotFound):
    message = _("Service %(service)s could not be found.")


class ServiceAlreadyExists(Conflict):
    message = _("A service with UUID %(uuid)s already exists.")


class ServiceListNotFound(ResourceNotFound):
    message = _("Service list could not be found for Bay %(bay_uuid)s.")


class ServiceCreationFailed(Invalid):
    message = _("Service creation failed for Bay %(bay_uuid)s.")


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
    """The code here changed to 400 according to the latest document."""
    message = _("Image %(image_id)s could not be found.")
    code = 400


class ImageNotAuthorized(MagnumException):
    message = _("Not authorized for image %(image_id)s.")


class OSDistroFieldNotFound(ResourceNotFound):
    """The code here changed to 400 according to the latest document."""
    message = _("Image %(image_id)s doesn't contain os_distro field.")
    code = 400


class KubernetesAPIFailed(MagnumException):
    def __init__(self, message=None, err=None, **kwargs):
        if err:
            if err.body:
                message = json.loads(err.body)['message']
            else:
                message = err.reason
            self.__class__.code = err.status
        else:
            self.__class__.code = kwargs.get('code')
        super(KubernetesAPIFailed, self).__init__(message, **kwargs)


class X509KeyPairNotFound(ResourceNotFound):
    message = _("A key pair %(x509keypair)s could not be found.")


class X509KeyPairAlreadyExists(Conflict):
    message = _("A key pair with UUID %(uuid)s already exists.")


class CertificateStorageException(MagnumException):
    message = _("Could not store certificate: %(msg)s")


class CertificateValidationError(Invalid):
    message = _("Extension '%(extension)s' not allowed")


class KeyPairNotFound(ResourceNotFound):
    message = _("Unable to find keypair %(keypair)s.")


class MagnumServiceNotFound(ResourceNotFound):
    message = _("A magnum service %(magnum_service_id)s could not be found.")


class MagnumServiceAlreadyExists(Conflict):
    message = _("A magnum service with ID %(id)s already exists.")


class UnsupportedK8sQuantityFormat(MagnumException):
    message = _("Unsupported quantity format for k8s bay.")


class UnsupportedDockerQuantityFormat(MagnumException):
    message = _("Unsupported quantity format for Swarm bay.")


class FlavorNotFound(ResourceNotFound):
    """The code here changed to 400 according to the latest document."""
    message = _("Unable to find flavor %(flavor)s.")
    code = 400


class NetworkNotFound(ResourceNotFound):
    """The code here changed to 400 according to the latest document."""
    message = _("Unable to find network %(network)s.")
    code = 400


class TrustCreateFailed(MagnumException):
    message = _("Failed to create trust for trustee %(trustee_user_id)s.")


class TrustDeleteFailed(MagnumException):
    message = _("Failed to delete trust %(trust_id)s.")


class TrusteeCreateFailed(MagnumException):
    message = _("Failed to create trustee %(username)s "
                "in domain %(domain_id)s")


class TrusteeDeleteFailed(MagnumException):
    message = _("Failed to delete trustee %(trustee_id)s")


class QuotaAlreadyExists(Conflict):
    message = _("Quota for project %(project_id)s already exists "
                "for resource %(resource)s.")


class RegionsListFailed(MagnumException):
    message = _("Failed to list regions.")


class TrusteeOrTrustToBayFailed(MagnumException):
    message = _("Failed to create trustee or trust for Bay: %(bay_uuid)s")


class CertificatesToBayFailed(MagnumException):
    message = _("Failed to create certificates for Bay: %(bay_uuid)s")
