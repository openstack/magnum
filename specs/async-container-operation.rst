=================================
Asynchronous Container Operations
=================================

Launchpad blueprint:

https://blueprints.launchpad.net/magnum/+spec/async-container-operations

At present, container operations are done in a synchronous way, end-to-end.
This model does not scale well, and incurs a penalty on the client to be
stuck till the end of completion of the operation.

Problem Description
-------------------

At present Magnum-Conductor executes the container operation as part of
processing the request forwarded from Magnum-API. For
container-create, if the image needs to be pulled down, it may take
a while depending on the responsiveness of the registry, which can be a
substantial delay. At the same time, experiments suggest that even for
pre-pulled image, the time taken by each operations, namely
create/start/delete, are in the same order, as it involves complete turn
around between the magnum-client and the COE-API, via Magnum-API and
Magnum-Conductor[1].

Use Cases
---------

For wider enterprise adoption of Magnum, we need it to scale better.
For that we need to replace some of these synchronous behaviors with
suitable alternative of asynchronous implementation.

To understand the use-case better, we can have a look at the average
time spent during container operations, as noted at[1].

Proposed Changes
----------------

The design has been discussed over the ML[6]. The conclusions have been kept
on the 'whiteboard' of the Blueprint.

The amount of code change is expected to be significant. To ease the
process of adoption, code review, functional tests, an approach of phased
implementation may be required. We can define the scope of the three phases of
the implementation as follows -

* Phase-0 will bring in the basic feature of asynchronous mode of operation in
  Magnum - (A) from API to Conductor and (B) from Conductor to COE-API. During
  phase-0, this mode will be optional through configuration.

  Both the communications of (A) and (B) are proposed to be made asynchronous
  to achieve the best of it. If we do (A) alone, it does not gain us much, as
  (B) takes up the higher cycles of the operation. If we do (B) alone, it does
  not make sense, as (A) will synchronously wait for no meaningful data.

* Phase-1 will concentrate on making the feature persistent to address various
  scenarios of conductor restart, worker failure etc. We will support this
  feature for multiple Conductor-workers in this phase.

* Phase-2 will select asynchronous mode of operation as the default mode. At
  the same time, we can evaluate to drop the code for synchronous mode, too.


Phase-0 is required as a meaningful temporary step, to establish the
importance and tangible benefits of phase-1. This is also to serve as a
proof-of-concept at a lower cost of code changes with a configurable option.
This will enable developers and operators to have a taste of the feature,
before bringing in the heavier dependencies and changes proposed in phase-1.

A reference implementation for the phase-0 items, has been put for review[2].

Following is the summary of the design -

1. Configurable mode of operation - async
-----------------------------------------

For ease of adoption, the async_mode of communication between API-conductor,
conductor-COE in magnum, can be controlled using a configuration option. So
the code-path for sync mode and async mode would co-exist for now. To achieve
this with minimal/no code duplication and cleaner interface, we are using
openstack/futurist[4]. Futurist interface hides the details of type of executor
being used. In case of async configuration, a greenthreadpool of configured
poolsize gets created. Here is a sample of how the config would look
like: ::

      [DEFAULT]
      async_enable = False

      [conductor]
      async_threadpool_max_workers = 64

Futurist library is used in oslo.messaging. Thus, it is used by almost all
OpenStack projects, in effect. Futurist is very useful to run same code
under different execution model and hence saving potential duplication of
code.


2. Type of operations
---------------------

There are two classes of container operations - one that can be made async,
namely create/delete/start/stop/pause/unpause/reboot, which do not need data
about the container in return. The other type requires data, namely
container-logs. For async-type container-operations, magnum-API will be
using 'cast' instead of 'call' from oslo_messaging[5].

'cast' from oslo.messaging.rpcclient is used to invoke a method and return
immediately, whereas 'call' invokes a method and waits for a reply. While
operating in asynchronous mode, it is intuitive to use cast method, as the
result of the response may not be available immediately.

Magnum-api first fetches the details of a container, by doing
'get_rpc_resource'. This function uses magnum objects. Hence, this function
uses a 'call' method underneath. Once, magnum-api gets back the details,
it issues the container operation next, using another 'call' method.
The above proposal is to replace the second 'call' with 'cast'.

If user issues a container operation, when there is no listening
conductor (because of process failure), there will be a RPC timeout at the
first 'call' method. In this case, user will observe the request to
get blocked at client and finally fail with HTTP 500 ERROR, after the RPC
timeout, which is 60 seconds by default. This behavior is independent of the
usage of 'cast' or 'call' for the second message, mentioned above. This
behavior does not influence our design, but it is documented here for clarity
of understanding.


3. Ensuring the order of execution - Phase-0
--------------------------------------------

Magnum-conductor needs to ensure that for a given bay and given container,
the operations are executed in sequence. In phase-0, we want to demonstrate
how asynchronous behavior helps scaling. Asynchronous mode of container
operations would be supported for single magnum-conductor scenario, in
phase-0. If magnum-conductor crashes, there will be no recovery for the
operations accepted earlier - which means no persistence in phase-0, for
operations accepted by magnum-conductor. Multiple conductor scenario and
persistence will be addressed in phase-1 [please refer to the next section
for further details]. If COE crashes or does not respond, the error will be
detected, as it happens in sync mode, and reflected on the container-status.

Magnum-conductor will maintain a job-queue. Job-queue is indexed by bay-id and
container-id. A job-queue entry would contain the sequence of operations
requested for a given bay-id and container-id, in temporal order. A
greenthread will execute the tasks/operations in order for a given job-queue
entry, till the queue empties. Using a greenthread in this fashion saves us
from the cost and complexity of locking, along with functional correctness.
When request for new operation comes in, it gets appended to the corresponding
queue entry.

For a sequence of container operations, if an intermediate operation fails,
we will stop continuing the sequence. The community feels more confident to
start with this strictly defensive policy[17]. The failure will be logged
and saved into the container-object, which will help an operator be informed
better about the result of the sequence of container operations. We may revisit
this policy later, if we think it is too restrictive.

4. Ensuring the order of execution - phase-1
--------------------------------------------

The goal is to execute requests for a given bay and a given container in
sequence. In phase-1, we want to address persistence and capability of
supporting multiple magnum-conductor processes. To achieve this, we will
reuse the concepts laid out in phase-0 and use a standard library.

We propose to use taskflow[7] for this implementation. Magnum-conductors
will consume the AMQP message and post a task[8] on a taskflow jobboard[9].
Greenthreads from magnum-conductors would subscribe to the taskflow
jobboard as taskflow-conductors[10]. Taskflow jobboard is maintained with
a choice of persistent backend[11]. This will help address the concern of
persistence for accepted operations, when a conductor crashes. Taskflow
will ensure that tasks, namely container operations, in a job, namely a
sequence of operations for a given bay and container, would execute in
sequence. We can easily notice that some of the concepts used in phase-0
are reused as it is. For example, job-queue maps to jobboard here, use of
greenthread maps to the conductor concept of taskflow. Hence, we expect easier
migration from phase-0 to phase-1, with the choice of taskflow.

For taskflow jobboard[11], the available choices of backend are Zookeeper and
Redis. But, we plan to use MySQL as default choice of backend, for magnum
conductor jobboard use-case. This support will be added to taskflow. Later,
we may choose to support the flexibility of other backends like ZK/Redis via
configuration. But, phase-1 will keep the implementation simple with MySQL
backend and revisit this, if required.

Let's consider the scenarios of Conductor crashing -
 - If a task is added to jobboard, and conductor crashes after that,
   taskflow can assign a particular job to any available greenthread agents
   from other conductor instances. If the system was running with single
   magnum-conductor, it will wait for the conductor to come back and join.
 - A task is picked up and magnum-conductor crashes. In this case, the task
   is not complete from jobboard point-of-view. As taskflow detects the
   conductor going away, it assigns another available conductor.
 - When conductor picks up a message from AMQP, it will acknowledge AMQP,
   only after persisting it to jobboard. This will prevent losing the message,
   if conductor crashes after picking up the message from AMQP. Explicit
   acknowledgement from application may use NotificationResult.HANDLED[12]
   to AMQP. We may use the at-least-one-guarantee[13] feature in
   oslo.messaging[14], as it becomes available.

To summarize some of the important outcomes of this proposal -
 - A taskflow job represents the sequence of container operations on a given
   bay and given container. At a given point of time, the sequence may contain
   a single or multiple operations.
 - There will be a single jobboard for all conductors.
 - Task-flow conductors are multiple greenthreads from a given
   magnum-conductor.
 - Taskflow-conductor will run in 'blocking' mode[15], as those greenthreads
   have no other job than claiming and executing the jobs from jobboard.
 - Individual jobs are supposed to maintain a temporal sequence. So the
   taskflow-engine would be 'serial'[16].
 - The proposed model for a 'job' is to consist of a temporal sequence of
   'tasks' - operations on a given bay and a given container. Henceforth,
   it is expected that when a given operation, namely container-create is in
   progress, a request for container-start may come in. Adding the task to
   the existing job is intuitive to maintain the sequence of operations.

To fit taskflow exactly into our use-case, we may need to do two enhancements
in taskflow -
- Supporting mysql plugin as a DB backend for jobboard. Support for redis
exists, so it will be similar.
We do not see any technical roadblock for adding mysql support for taskflow
jobboard. If the proposal does not get approved by taskflow team, we may have
to use redis, as an alternative option.
- Support for dynamically adding tasks to a job on jobboard. This also looks
feasible, as discussed over the #openstack-state-management [Unfortunately,
this channel is not logged, but if we agree in this direction, we can initiate
discussion over ML, too]
If taskflow team does not allow adding this feature, even though they have
agreed now, we will use the dependency feature in taskflow. We will explore
and elaborate this further, if it requires.


5. Status of progress
---------------------

The progress of execution of a container operation is reflected on the status
of a container as - 'create-in-progress', 'delete-in-progress' etc.

Alternatives
------------

Without an asynchronous implementation, Magnum will suffer from complaints
about poor scalability and slowness.

In this design, stack-lock[3] has been considered as an alternative to
taskflow. Following are the reasons for preferring taskflow over
stack-lock, as of now,
- Stack-lock used in Heat is not a library, so it will require making a copy
for Magnum, which is not desirable.
- Taskflow is relatively mature, well supported, feature-rich library.
- Taskflow has in-built capacity to scale out[in] as multiple conductors
can join in[out] the cluster.
- Taskflow has a failure detection and recovery mechanism. If a process
crashes, then worker threads from other conductor may continue the execution.

In this design, we describe futurist[4] as a choice of implementation. The
choice was to prevent duplication of code for async and sync mode. For this
purpose, we could not find any other solution to compare.

Data model impact
-----------------

Phase-0 has no data model impact. But phase-1 may introduce an additional
table into the Magnum database. As per the present proposal for using taskflow
in phase-1, we have to introduce a new table for jobboard under magnum db.
This table will be exposed to taskflow library as a persistent db plugin.
Alternatively, an implementation with stack-lock will also require an
introduction of a new table for stack-lock objects.

REST API impact
---------------

None.

Security impact
---------------

None.

Notifications impact
--------------------

None

Other end user impact
---------------------

None

Performance impact
------------------

Asynchronous mode of operation helps in scalability. Hence, it improves
responsiveness and reduces the turn around time in a significant
proportion. A small test on devstack, comparing both the modes,
demonstrate this with numbers.[1]

Other deployer impact
---------------------

None.

Developer impact
----------------

None

Implementation
--------------

Assignee(s)
-----------

Primary assignee
  suro-patz(Surojit Pathak)

Work Items
----------

For phase-0
* Introduce config knob for asynchronous mode of container operations.

* Changes for Magnum-API to use CAST instead of CALL for operations eligible
  for asynchronous mode.

* Implement the in-memory job-queue in Magnum conductor, and integrate futurist
  library.

* Unit tests and functional tests for async mode.

* Documentation changes.

For phase-1
* Get the dependencies on taskflow being resolved.

* Introduce jobboard table into Magnum DB.

* Integrate taskflow in Magnum conductor to replace the in-memory job-queue
  with taskflow jobboard. Also, we need conductor greenthreads to subscribe
  as workers to the taskflow jobboard.

* Add unit tests and functional tests for persistence and multiple conductor
  scenario.

* Documentation changes.

For phase-2
* We will promote asynchronous mode of operation as the default mode of
operation.

* We may decide to drop the code for synchronous mode and corresponding config.

* Documentation changes.


Dependencies
------------

For phase-1, if we choose to implement using taskflow, we need to get
following two features added to taskflow first -
* Ability to add new task to an existing job on jobboard.
* mysql plugin support as persistent DB.

Testing
-------

All the existing test cases are run to ensure async mode does not break them.
Additionally more functional tests and unit tests will be added specific to
async mode.

Documentation Impact
--------------------

Magnum documentation will include a description of the option for asynchronous
mode of container operations and its benefits. We will also add to
developer documentation on guideline for implementing a container operation in
both the modes - sync and async. We will add a section on 'how to debug
container operations in async mode'. The phase-0 and phase-1 implementation
and their support for single or multiple conductors will be clearly documented
for the operators.

References
----------

[1] - Execution time comparison between sync and async modes:

https://gist.github.com/surojit-pathak/2cbdad5b8bf5b569e755

[2] - Proposed change under review:

https://review.openstack.org/#/c/267134/

[3] - Heat's use of stacklock

http://docs.openstack.org/developer/heat/_modules/heat/engine/stack_lock.html

[4] - openstack/futurist

http://docs.openstack.org/developer/futurist/

[5] - openstack/oslo.messaging

http://docs.openstack.org/developer/oslo.messaging/rpcclient.html

[6] - ML discussion on the design

http://lists.openstack.org/pipermail/openstack-dev/2015-December/082524.html

[7] - Taskflow library

http://docs.openstack.org/developer/taskflow/

[8] - task in taskflow

http://docs.openstack.org/developer/taskflow/atoms.html#task

[9] - job and jobboard in taskflow

http://docs.openstack.org/developer/taskflow/jobs.html

[10] - conductor in taskflow

http://docs.openstack.org/developer/taskflow/conductors.html

[11] - persistent backend support in taskflow

http://docs.openstack.org/developer/taskflow/persistence.html

[12] - oslo.messaging notification handler

http://docs.openstack.org/developer/oslo.messaging/notification_listener.html

[13] - Blueprint for at-least-once-guarantee, oslo.messaging

https://blueprints.launchpad.net/oslo.messaging/+spec/at-least-once-guarantee

[14] - Patchset under review for at-least-once-guarantee, oslo.messaging

https://review.openstack.org/#/c/229186/

[15] - Taskflow blocking mode for conductor

http://docs.openstack.org/developer/taskflow/conductors.html#taskflow.conductors.backends.impl_executor.ExecutorConductor

[16] - Taskflow serial engine

http://docs.openstack.org/developer/taskflow/engines.html

[17] - Community feedback on policy to handle failure within a sequence

http://eavesdrop.openstack.org/irclogs/%23openstack-containers/%23openstack-containers.2016-03-08.log.html#t2016-03-08T20:41:17
