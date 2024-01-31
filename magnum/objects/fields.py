#    Copyright 2015 Intel Corp.
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

from oslo_versionedobjects import fields


class ClusterStatus(fields.Enum):
    CREATE_IN_PROGRESS = 'CREATE_IN_PROGRESS'
    CREATE_FAILED = 'CREATE_FAILED'
    CREATE_COMPLETE = 'CREATE_COMPLETE'
    UPDATE_IN_PROGRESS = 'UPDATE_IN_PROGRESS'
    UPDATE_FAILED = 'UPDATE_FAILED'
    UPDATE_COMPLETE = 'UPDATE_COMPLETE'
    DELETE_IN_PROGRESS = 'DELETE_IN_PROGRESS'
    DELETE_FAILED = 'DELETE_FAILED'
    DELETE_COMPLETE = 'DELETE_COMPLETE'
    RESUME_COMPLETE = 'RESUME_COMPLETE'
    RESUME_FAILED = 'RESUME_FAILED'
    RESTORE_COMPLETE = 'RESTORE_COMPLETE'
    ROLLBACK_IN_PROGRESS = 'ROLLBACK_IN_PROGRESS'
    ROLLBACK_FAILED = 'ROLLBACK_FAILED'
    ROLLBACK_COMPLETE = 'ROLLBACK_COMPLETE'
    SNAPSHOT_COMPLETE = 'SNAPSHOT_COMPLETE'
    CHECK_COMPLETE = 'CHECK_COMPLETE'
    ADOPT_COMPLETE = 'ADOPT_COMPLETE'

    ALL = (CREATE_IN_PROGRESS, CREATE_FAILED, CREATE_COMPLETE,
           UPDATE_IN_PROGRESS, UPDATE_FAILED, UPDATE_COMPLETE,
           DELETE_IN_PROGRESS, DELETE_FAILED, DELETE_COMPLETE,
           RESUME_COMPLETE, RESUME_FAILED, RESTORE_COMPLETE,
           ROLLBACK_IN_PROGRESS, ROLLBACK_FAILED, ROLLBACK_COMPLETE,
           SNAPSHOT_COMPLETE, CHECK_COMPLETE, ADOPT_COMPLETE)

    STATUS_FAILED = (CREATE_FAILED, UPDATE_FAILED,
                     DELETE_FAILED, ROLLBACK_FAILED, RESUME_FAILED)

    def __init__(self):
        super(ClusterStatus, self).__init__(valid_values=ClusterStatus.ALL)


class ClusterHealthStatus(fields.Enum):
    HEALTHY = 'HEALTHY'
    UNHEALTHY = 'UNHEALTHY'
    UNKNOWN = 'UNKNOWN'

    ALL = (HEALTHY, UNHEALTHY, UNKNOWN)

    STATUS_FAILED = (UNHEALTHY)

    def __init__(self):
        super(ClusterHealthStatus, self).__init__(
            valid_values=ClusterHealthStatus.ALL)


class FederationStatus(fields.Enum):
    CREATE_IN_PROGRESS = 'CREATE_IN_PROGRESS'
    CREATE_FAILED = 'CREATE_FAILED'
    CREATE_COMPLETE = 'CREATE_COMPLETE'
    UPDATE_IN_PROGRESS = 'UPDATE_IN_PROGRESS'
    UPDATE_FAILED = 'UPDATE_FAILED'
    UPDATE_COMPLETE = 'UPDATE_COMPLETE'
    DELETE_IN_PROGRESS = 'DELETE_IN_PROGRESS'
    DELETE_FAILED = 'DELETE_FAILED'
    DELETE_COMPLETE = 'DELETE_COMPLETE'

    ALL = (CREATE_IN_PROGRESS, CREATE_FAILED, CREATE_COMPLETE,
           UPDATE_IN_PROGRESS, UPDATE_FAILED, UPDATE_COMPLETE,
           DELETE_IN_PROGRESS, DELETE_FAILED, DELETE_COMPLETE)

    STATUS_FAILED = (CREATE_FAILED, UPDATE_FAILED, DELETE_FAILED)

    def __init__(self):
        super(FederationStatus, self).__init__(
            valid_values=FederationStatus.ALL)


class ContainerStatus(fields.Enum):
    ALL = (
        ERROR, RUNNING, STOPPED, PAUSED, UNKNOWN,
    ) = (
        'Error', 'Running', 'Stopped', 'Paused', 'Unknown',
    )

    def __init__(self):
        super(ContainerStatus, self).__init__(
            valid_values=ContainerStatus.ALL)


class ClusterType(fields.Enum):
    ALL = (
        KUBERNETES,
    ) = (
        'kubernetes',
    )

    def __init__(self):
        super(ClusterType, self).__init__(valid_values=ClusterType.ALL)


class QuotaResourceName(fields.Enum):
    ALL = (
        CLUSTER,
    ) = (
        'Cluster',
    )

    def __init__(self):
        super(QuotaResourceName, self).__init__(
            valid_values=QuotaResourceName.ALL)


class ServerType(fields.Enum):
    ALL = (
        VM, BM,
    ) = (
        'vm', 'bm',
    )

    def __init__(self):
        super(ServerType, self).__init__(
            valid_values=ServerType.ALL)


class MagnumServiceState(fields.Enum):
    ALL = (
        up, down
    ) = (
        'up', 'down',
    )

    def __init__(self):
        super(MagnumServiceState, self).__init__(
            valid_values=MagnumServiceState.ALL)


class MagnumServiceBinary(fields.Enum):
    ALL = (
        magnum_conductor
    ) = (
        'magnum-conductor',
    )

    def __init__(self):
        super(MagnumServiceBinary, self).__init__(
            valid_values=MagnumServiceBinary.ALL)


class ListOfDictsField(fields.AutoTypedField):
    AUTO_TYPE = fields.List(fields.Dict(fields.FieldType()))


class ClusterStatusField(fields.BaseEnumField):
    AUTO_TYPE = ClusterStatus()


class ClusterHealthStatusField(fields.BaseEnumField):
    AUTO_TYPE = ClusterHealthStatus()


class MagnumServiceField(fields.BaseEnumField):
    AUTO_TYPE = MagnumServiceState()


class MagnumServiceBinaryField(fields.BaseEnumField):
    AUTO_TYPE = MagnumServiceBinary()


class ContainerStatusField(fields.BaseEnumField):
    AUTO_TYPE = ContainerStatus()


class ClusterTypeField(fields.BaseEnumField):
    AUTO_TYPE = ClusterType()


class ServerTypeField(fields.BaseEnumField):
    AUTO_TYPE = ServerType()


class FederationStatusField(fields.BaseEnumField):
    AUTO_TYPE = FederationStatus()
