# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.


from magnum.common import exception
from magnum.openstack.common._i18n import _
from magnum.tests import base


class TestMagnumException(exception.MagnumException):
    message = _("templated %(name)s")


class TestException(base.BaseTestCase):
    def setUp(self):
        super(TestException, self).setUp()

    def raise_(self, ex):
        raise ex

    def test_message_is_templated(self):
        ex = TestMagnumException(name="NAME")
        self.assertEqual(ex.message, "templated NAME")

    def test_custom_message_is_templated(self):
        ex = TestMagnumException(_("custom templated %(name)s"), name="NAME")
        self.assertEqual(ex.message, "custom templated NAME")

    def test_ObjectNotFound(self):
        self.assertRaises(exception.ObjectNotFound,
                    lambda: self.raise_(exception.ObjectNotFound()))

    def test_ObjectNotUnique(self):
        self.assertRaises(exception.ObjectNotUnique,
                    lambda: self.raise_(exception.ObjectNotUnique()))

    def test_ResourceNotFound(self):
        self.assertRaises(exception.ResourceNotFound,
                    lambda: self.raise_(exception.ResourceNotFound()))

    def test_ResourceExists(self):
        self.assertRaises(exception.ResourceExists,
                    lambda: self.raise_(exception.ResourceExists()))

    def test_AuthorizationFailure(self):
        self.assertRaises(exception.AuthorizationFailure,
                    lambda: self.raise_(exception.AuthorizationFailure()))

    def test_UnsupportedObjectError(self):
        self.assertRaises(exception.UnsupportedObjectError,
                    lambda: self.raise_(exception.UnsupportedObjectError()))

    def test_IncompatibleObjectVersion(self):
        self.assertRaises(exception.IncompatibleObjectVersion,
                    lambda: self.raise_(exception.IncompatibleObjectVersion()))

    def test_OrphanedObjectError(self):
        self.assertRaises(exception.OrphanedObjectError,
                    lambda: self.raise_(exception.OrphanedObjectError()))

    def test_Invalid(self):
        self.assertRaises(exception.Invalid,
                    lambda: self.raise_(exception.Invalid()))

    def test_InvalidUUID(self):
        self.assertRaises(exception.InvalidUUID,
                    lambda: self.raise_(exception.InvalidUUID()))

    def test_InvalidName(self):
        self.assertRaises(exception.InvalidName,
                    lambda: self.raise_(exception.InvalidName()))

    def test_InvalidUuidOrName(self):
        self.assertRaises(exception.InvalidUuidOrName,
                    lambda: self.raise_(exception.InvalidUuidOrName()))

    def test_InvalidIdentity(self):
        self.assertRaises(exception.InvalidIdentity,
                    lambda: self.raise_(exception.InvalidIdentity()))

    def test_HTTPNotFound(self):
        self.assertRaises(exception.HTTPNotFound,
                    lambda: self.raise_(exception.HTTPNotFound()))

    def test_Conflict(self):
        self.assertRaises(exception.Conflict,
                    lambda: self.raise_(exception.Conflict()))

    def test_InvalidState(self):
        self.assertRaises(exception.InvalidState,
                    lambda: self.raise_(exception.InvalidState()))

    def test_InvalidParameterValue(self):
        self.assertRaises(exception.InvalidParameterValue,
                    lambda: self.raise_(exception.InvalidParameterValue()))

    def test_InstanceAssociated(self):
        self.assertRaises(exception.InstanceAssociated,
                    lambda: self.raise_(exception.InstanceAssociated()))

    def test_InstanceNotFound(self):
        self.assertRaises(exception.InstanceNotFound,
                    lambda: self.raise_(exception.InstanceNotFound()))

    def test_PatchError(self):
        self.assertRaises(exception.PatchError,
                    lambda: self.raise_(exception.PatchError()))

    def test_NotAuthorized(self):
        self.assertRaises(exception.NotAuthorized,
                    lambda: self.raise_(exception.NotAuthorized()))

    def test_OperationNotPermitted(self):
        self.assertRaises(exception.OperationNotPermitted,
                    lambda: self.raise_(exception.OperationNotPermitted()))

    def test_InvalidMAC(self):
        self.assertRaises(exception.InvalidMAC,
                    lambda: self.raise_(exception.InvalidMAC()))

    def test_SSHConnectFailed(self):
        self.assertRaises(exception.SSHConnectFailed,
                    lambda: self.raise_(exception.SSHConnectFailed()))

    def test_FileSystemNotSupported(self):
        self.assertRaises(exception.FileSystemNotSupported,
                    lambda: self.raise_(exception.FileSystemNotSupported()))

    def test_BayNotFound(self):
        self.assertRaises(exception.BayNotFound,
                    lambda: self.raise_(exception.BayNotFound()))

    def test_BayAlreadyExists(self):
        self.assertRaises(exception.BayAlreadyExists,
                    lambda: self.raise_(exception.BayAlreadyExists()))

    def test_BayModelNotFound(self):
        self.assertRaises(exception.BayModelNotFound,
                    lambda: self.raise_(exception.BayModelNotFound()))

    def test_BayModelAlreadyExists(self):
        self.assertRaises(exception.BayModelAlreadyExists,
                    lambda: self.raise_(exception.BayModelAlreadyExists()))

    def test_BayModelReferenced(self):
        self.assertRaises(exception.BayModelReferenced,
                    lambda: self.raise_(exception.BayModelReferenced()))

    def test_ContainerNotFound(self):
        self.assertRaises(exception.ContainerNotFound,
                    lambda: self.raise_(exception.ContainerNotFound()))

    def test_ContainerAlreadyExists(self):
        self.assertRaises(exception.ContainerAlreadyExists,
                    lambda: self.raise_(exception.ContainerAlreadyExists()))

    def test_PodNotFound(self):
        self.assertRaises(exception.PodNotFound,
                    lambda: self.raise_(exception.PodNotFound()))

    def test_PodAlreadyExists(self):
        self.assertRaises(exception.PodAlreadyExists,
                    lambda: self.raise_(exception.PodAlreadyExists()))

    def test_ReplicationControllerNotFound(self):
        self.assertRaises(exception.ReplicationControllerNotFound,
           lambda: self.raise_(exception.ReplicationControllerNotFound()))

    def test_ReplicationControllerAlreadyExists(self):
        self.assertRaises(exception.ReplicationControllerAlreadyExists,
         lambda: self.raise_(exception.ReplicationControllerAlreadyExists()))

    def test_ServiceNotFound(self):
        self.assertRaises(exception.ServiceNotFound,
                    lambda: self.raise_(exception.ServiceNotFound()))

    def test_ServiceAlreadyExists(self):
        self.assertRaises(exception.ServiceAlreadyExists,
                    lambda: self.raise_(exception.ServiceAlreadyExists()))

    def test_ConfigInvalid(self):
        self.assertRaises(exception.ConfigInvalid,
                    lambda: self.raise_(exception.ConfigInvalid()))

    def test_NodeAlreadyExists(self):
        self.assertRaises(exception.NodeAlreadyExists,
                    lambda: self.raise_(exception.NodeAlreadyExists()))

    def test_NodeNotFound(self):
        self.assertRaises(exception.NodeNotFound,
                    lambda: self.raise_(exception.NodeNotFound()))

    def test_NodeAssociated(self):
        self.assertRaises(exception.NodeAssociated,
                    lambda: self.raise_(exception.NodeAssociated()))
