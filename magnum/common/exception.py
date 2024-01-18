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

from keystoneclient import exceptions as keystone_exceptions
from oslo_config import cfg
from oslo_log import log as logging

import magnum.conf
from magnum.i18n import _


LOG = logging.getLogger(__name__)

CONF = magnum.conf.CONF

try:
    CONF.import_opt('fatal_exception_format_errors',
                    'oslo_versionedobjects.exception')
except cfg.NoSuchOptError:
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
        except Exception:
            # kwargs doesn't match a variable in the message
            # log the issue and the kwargs
            LOG.exception('Exception in string format operation, '
                          'kwargs: %s', kwargs)
            try:
                if CONF.fatal_exception_format_errors:
                    raise
            except cfg.NoSuchOptError:
                # Note: work around for Bug: #1447873
                if CONF.oslo_versionedobjects.fatal_exception_format_errors:
                    raise

        super(MagnumException, self).__init__(self.message)

    def __str__(self):
        return self.message

    def __unicode__(self):
        return self.message

    def format_message(self):
        if self.__class__.__name__.endswith('_Remote'):
            return self.args[0]
        else:
            return str(self)


class ObjectNotFound(MagnumException):
    message = _("The %(name)s %(id)s could not be found.")
    code = 404


class ProjectNotFound(ObjectNotFound):
    message = _("The %(name)s %(id)s could not be found.")


class ResourceNotFound(ObjectNotFound):
    message = _("The %(name)s resource %(id)s could not be found.")


class AuthorizationFailure(MagnumException):
    message = _("%(client)s connection failed. %(message)s")
    code = 403


class Invalid(MagnumException):
    message = _("Unacceptable parameters.")
    code = 400


class InvalidUUID(Invalid):
    message = _("Expected a uuid but received %(uuid)s.")


class InvalidName(Invalid):
    message = _("Expected a name but received %(name)s.")


class InvalidDiscoveryURL(Invalid):
    message = _("Received invalid discovery URL '%(discovery_url)s' for "
                "discovery endpoint '%(discovery_endpoint)s'.")


class GetDiscoveryUrlFailed(MagnumException):
    message = _("Failed to get discovery url from '%(discovery_endpoint)s'.")


class InvalidClusterDiscoveryURL(Invalid):
    message = _("Invalid discovery URL '%(discovery_url)s'.")


class InvalidClusterSize(Invalid):
    message = _("Expected cluster size %(expect_size)d but get cluster "
                "size %(size)d from '%(discovery_url)s'.")


class GetClusterSizeFailed(MagnumException):
    message = _("Failed to get the size of cluster from '%(discovery_url)s'.")


class InvalidIdentity(Invalid):
    message = _("Expected an uuid or int but received %(identity)s.")


class InvalidCsr(Invalid):
    message = _("Received invalid csr %(csr)s.")


class InvalidSubnet(Invalid):
    message = _("Received invalid subnet %(subnet)s.")


class InvalidVersion(Invalid):
    message = _("Received invalid tag for %(tag)s.")


class HTTPNotFound(ResourceNotFound):
    pass


class Conflict(MagnumException):
    message = _('Conflict.')
    code = 409


class ApiVersionsIntersect(Invalid):
    message = _("Version of %(name)s %(min_ver)s %(max_ver)s intersects "
                "with another versions.")


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


class InvalidDNS(Invalid):
    message = _(
        "Expected a single dns address or comma separated dns list, "
        "but received %(dns)s.")


class ConfigInvalid(Invalid):
    message = _("Invalid configuration file. %(error_msg)s")


class ClusterTemplateNotFound(ResourceNotFound):
    message = _("ClusterTemplate %(clustertemplate)s could not be found.")


class ClusterTemplateAlreadyExists(Conflict):
    message = _("A ClusterTemplate with UUID %(uuid)s already exists.")


class ClusterTemplateReferenced(Invalid):
    message = _("ClusterTemplate %(clustertemplate)s is referenced by one or"
                " multiple clusters.")


class ClusterTemplatePublishDenied(NotAuthorized):
    message = _("Not authorized to set public or hidden flag for cluster"
                " template.")


class ClusterNotFound(ResourceNotFound):
    message = _("Cluster %(cluster)s could not be found.")


class ClusterAlreadyExists(Conflict):
    message = _("A cluster with UUID %(uuid)s already exists.")


class NotSupported(MagnumException):
    message = _("%(operation)s is not supported.")
    code = 400


class ClusterTypeNotSupported(NotSupported):
    message = _("Cluster type (%(server_type)s, %(os)s, %(coe)s)"
                " not supported.")


class ClusterDriverNotSupported(NotSupported):
    message = _("Cluster driver (%(driver_name)s) not supported.")


class RequiredParameterNotProvided(Invalid):
    message = _("Required parameter %(heat_param)s not provided.")


class OperationInProgress(Invalid):
    message = _("Cluster %(cluster_name)s already has an operation in "
                "progress.")


class VolumeTypeNotFound(ResourceNotFound):
    """The code here changed to 400 according to the latest document."""
    message = _("Valid volume type could not be found.")
    code = 400


class ImageNotFound(ResourceNotFound):
    """The code here changed to 400 according to the latest document."""
    message = _("Image %(image_id)s could not be found.")
    code = 400


class ImageNotAuthorized(NotAuthorized):
    message = _("Not authorized for image %(image_id)s.")


class OSDistroFieldNotFound(ResourceNotFound):
    """The code here changed to 400 according to the latest document."""
    message = _("Image %(image_id)s doesn't contain os_distro field.")
    code = 400


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


class UnsupportedK8sQuantityFormat(Invalid):
    message = _("Unsupported quantity format for k8s cluster.")


class FlavorNotFound(ResourceNotFound):
    """The code here changed to 400 according to the latest document."""
    message = _("Unable to find flavor %(flavor)s.")
    code = 400


class FixedNetworkNotFound(ResourceNotFound):
    """The code here changed to 400 according to the latest document."""
    """"Ensure the network is private."""
    message = _("Unable to find fixed network %(network)s.")
    code = 400


class FixedSubnetNotFound(ResourceNotFound):
    """The code here changed to 400 according to the latest document."""
    message = _("Unable to find fixed subnet %(subnet)s.")
    code = 400


class ExternalNetworkNotFound(ResourceNotFound):
    """The code here changed to 400 according to the latest document."""
    """"Ensure the network is not private."""
    message = _("Unable to find external network %(network)s.")
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


class QuotaNotFound(ResourceNotFound):
    message = _("Quota could not be found: %(msg)s")


class ResourceLimitExceeded(NotAuthorized):
    message = _('Resource limit exceeded: %(msg)s')


class RegionsListFailed(MagnumException):
    message = _("Failed to list regions.")


class ServicesListFailed(MagnumException):
    message = _("Failed to list services.")


class TrusteeOrTrustToClusterFailed(MagnumException):
    message = _("Failed to create trustee or trust for Cluster: "
                "%(cluster_uuid)s")


class CertificatesToClusterFailed(MagnumException):
    message = _("Failed to create certificates for Cluster: %(cluster_uuid)s")


class FederationNotFound(ResourceNotFound):
    message = _("Federation %(federation)s could not be found.")


class FederationAlreadyExists(Conflict):
    message = _("A federation with UUID %(uuid)s already exists.")


class MemberAlreadyExists(Conflict):
    message = _("A cluster with UUID %(uuid)s is already a member of the "
                "federation %(federation_name)s.")


class PreDeletionFailed(Conflict):
    message = _("Failed to pre-delete resources for cluster %(cluster_uuid)s, "
                "error: %(msg)s.")


class NodeGroupAlreadyExists(Conflict):
    message = _("A node group with name %(name)s already exists in the "
                "cluster %(cluster_id)s.")


class NodeGroupNotFound(ResourceNotFound):
    message = _("Nodegroup %(nodegroup)s could not be found.")


class MasterNGSizeInvalid(InvalidParameterValue):
    message = _("master nodegroup size of %(requested_size)s is invalid, "
                "size cannot be an even number.")


class MasterNGResizeNotSupported(NotSupported):
    message = _("Resizing the master nodegroup is not supported "
                "by this driver.")


class ZeroNodeCountNotSupported(NotSupported):
    message = _("Resizing a nodegroup to zero is not supported in the "
                "provided microversion.")


class ClusterUpgradeNotSupported(NotSupported):
    message = _("Cluster upgrade is not supported in the "
                "provided microversion.")


class NGResizeOutBounds(Invalid):
    message = _("Resizing %(nodegroup)s outside the allowed range: "
                "min_node_count = %(min_nc)s, "
                "max_node_count = %(max_nc)s")


class DeletingDefaultNGNotSupported(NotSupported):
    message = _("Deleting a default nodegroup is not supported.")


class NodeGroupInvalidInput(Conflict):
    message = _("%(attr)s for %(nodegroup)s is invalid (%(expl)s).")


class CreateMasterNodeGroup(NotSupported):
    message = _("Creating master nodegroups is currently not supported.")


class NgOperationInProgress(Invalid):
    message = _("Nodegroup %(nodegroup)s already has an operation in "
                "progress.")


class InvalidClusterTemplateForUpgrade(Conflict):
    message = _("Cluster Template is not valid for upgrade: %(reason)s")


class ClusterAPIAddressUnavailable(Conflict):
    message = _("Cluster API address is not available yet")


class ObjectError(MagnumException):
    message = _("Failed to perform action %{action}s on %{obj_name}s with "
                "uuid %{obj_id}s: %{reason}s")
