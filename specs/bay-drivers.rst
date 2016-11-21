..
   This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

======================================
Container Orchestration Engine drivers
======================================

Launchpad blueprint:

https://blueprints.launchpad.net/magnum/+spec/bay-drivers

Container Orchestration Engines (COEs) are different systems for managing
containerized applications in a clustered environment, each having their own
conventions and ecosystems. Three of the most common, which also happen to be
supported in Magnum, are: Docker Swarm, Kubernetes, and Mesos. In order to
successfully serve developers, Magnum needs to be able to provision and manage
access to the latest COEs through its API in an effective and scalable way.


Problem description
===================

Magnum currently supports the three most popular COEs, but as more emerge and
existing ones change, it needs an effective and scalable way of managing
them over time.

One of the problems with the current implementation is that COE-specific logic,
such as Kubernetes replication controllers and services, is situated in the
core Magnum library and made available to users through the main API. Placing
COE-specific logic in a core API introduces tight coupling and forces
operators to work with an inflexible design.

By formalising a more modular and extensible architecture, Magnum will be
in a much better position to help operators and consumers satisfy custom
use-cases.

Use cases
---------

1. Extensibility. Contributors and maintainers need a suitable architecture to
   house current and future COE implementations. Moving to a more extensible
   architecture, where core classes delegate to drivers, provides a more
   effective and elegant model for handling COE differences without the need
   for tightly coupled and monkey-patched logic.

   One of the key use cases is allowing operators to customise their
   orchestration logic, such as modifying Heat templates or even using their
   own tooling like Ansible. Moreover, operators will often expect to use a
   custom distro image with lots of software pre-installed and many special
   security requirements that is extremely difficult or impossible to do with
   the current upstream templates. COE drivers solves these problems.

2. Maintainability. Moving to a modular architecture will be easier to manage
   in the long-run because the responsibility of maintaining non-standard
   implementations is shifted into the operator's domain. Maintaining the
   default drivers which are packaged with Magnum will also be easier and
   cleaner since logic is now demarcated from core codebase directories.

3. COE & Distro choice. In the community there has been a lot of discussion
   about which distro and COE combination to support with the templates.
   Having COE drivers allows for people or organizations to maintain
   distro-specific implementations (e.g CentOS+Kubernetes).

4. Addresses dependency concerns. One of the direct results of
   introducing a driver model is the ability to give operators more freedom
   about choosing how Magnum integrates with the rest of their OpenStack
   platform. For example, drivers would remove the necessity for users to
   adopt Barbican for secret management.

5. Driver versioning. The new driver model allows operators to modify existing
   drivers or creating custom ones, release new bay types based on the newer
   version, and subsequently launch news bays running the updated
   functionality. Existing bays which are based on older driver versions would
   be unaffected in this process and would still be able to have lifecycle
   operations performed on them. If one were to list their details from the
   API, it would reference the old driver version. An operator can see which
   driver version a bay type is based on through its ``driver`` value,
   which is exposed through the API.

Proposed change
===============

1. The creation of new directory at the project root: ``./magnum/drivers``.
   Each driver will house its own logic inside its own directory. Each distro
   will house its own logic inside that driver directory. For example, the
   Fedora Atomic distro using Swarm will have the following directory
   structure:

   ::

      drivers/
        swarm_atomic_v1/
            image/
              ...
            templates/
              ...
            api.py
            driver.py
            monitor.py
            scale.py
            template_def.py
            version.py


   The directory name should be a string which uniquely identifies the driver
   and provides a descriptive reference. The driver version number and name are
   provided in the manifest file and will be  included in the bay metadata at
   cluster build time.

   There are two workflows for rolling out driver updates:

   - if the change is relatively minor, they modify the files in the
     existing driver directory and update the version number in the manifest
     file.

   - if the change is significant, they create a new directory
     (either from scratch or by forking).

   Further explanation of the three top-level files:

   - an ``image`` directory is *optional* and should contain documentation
     which tells users how to build the image and register it to glance. This
     directory can also hold artifacts for building the image, for instance
     diskimagebuilder elements, scripts, etc.

   - a ``templates`` directory is *required* and will (for the foreseeable
     future) store Heat template YAML files. In the future drivers will allow
     operators to use their own orchestration tools like Ansible.

   - ``api.py`` is *optional*, and should contain the API controller which
     handles custom API operations like Kubernetes RCs or Pods. It will be
     this class which accepts HTTP requests and delegates to the Conductor. It
     should contain a uniquely named class, such as ``SwarmAtomicXYZ``, which
     extends from the core controller class. The COE class would have the
     opportunity of overriding base methods if necessary.

   - ``driver.py`` is *required*, and should contain the logic which maps
     controller actions to COE interfaces. These include: ``bay_create``,
     ``bay_update``, ``bay_delete``, ``bay_rebuild``, ``bay_soft_reboot`` and
     ``bay_hard_reboot``.

   - ``version.py`` is *required*, and should contain the version number of
     the bay driver. This is defined by a ``version`` attribute and is
     represented in the ``1.0.0`` format. It should also include a ``Driver``
     attribute and should be a descriptive name such as ``swarm_atomic``.

     Due to the varying nature of COEs, it is up to the bay
     maintainer to implement this in their own way. Since a bay is a
     combination of a COE and an image, ``driver.py`` will also contain
     information about the ``os_distro`` property which is expected to be
     attributed to Glance image.

   - ``monitor.py`` is *optional*, and should contain the logic which monitors
     the resource utilization of bays.

   - ``template_def.py`` is *required* and should contain the COE's
     implementation of how orchestration templates are loaded and matched to
     Magnum objects. It would probably contain multiple classes, such as
     ``class SwarmAtomicXYZTemplateDef(BaseTemplateDefinition)``.

   - ``scale.py`` is *optional* per bay specification and should contain the
     logic for scaling operations.

2. Renaming the ``coe`` attribute of BayModel to ``driver``. Because this
   value would determine which driver classes and orchestration templates to
   load, it would need to correspond to the name of the driver as it is
   registered with stevedore_ and setuptools entry points.

   During the lifecycle of an API operation, top-level Magnum classes (such as
   a Bay conductor) would then delegate to the driver classes which have been
   dynamically loaded. Validation will need to ensure that whichever value
   is provided by the user is correct.

   By default, drivers are located under the main project directory and their
   namespaces are accessible via ``magnum.drivers.foo``. But a use case that
   needs to be looked at and, if possible, provided for is drivers which are
   situated outside the project directory, for example in
   ``/usr/share/magnum``. This will suit operators who want greater separation
   between customised code and Python libraries.

3. The driver implementations for the 3 current COE and Image combinations:
   Docker Swarm Fedora, Kubernetes Fedora, Kubernetes CoreOS, and Mesos
   Ubuntu. Any templates would need to be moved from
   ``magnum/templates/{coe_name}`` to
   ``magnum/drivers/{driver_name}/templates``.

4. Removal of the following files:

   ::

    magnum/magnum/conductor/handlers/
      docker_conductor.py
      k8s_conducter.py

Design Principles
-----------------

- Minimal, clean API without a high cognitive burden

- Ensure Magnum's priority is to do one thing well, but allow extensibility
  by external contributors

- Do not force ineffective abstractions that introduce feature divergence

- Formalise a modular and loosely coupled driver architecture that removes
  COE logic from the core codebase


Alternatives
------------

This alternative relates to #5 of Proposed Change. Instead of having a
drivers registered using stevedore_ and setuptools entry points, an alternative
is to use the Magnum config instead.


Data model impact
-----------------

Since drivers would be implemented for the existing COEs, there would be
no loss of functionality for end-users.


REST API impact
---------------

Attribute change when creating and updating a BayModel (``coe`` to
``driver``). This would occur before v1 of the API is frozen.

COE-specific endpoints would be removed from the core API.


Security impact
---------------

None


Notifications impact
--------------------

None


Other end user impact
---------------------

There will be deployer impacts because deployers will need to select
which drivers they want to activate.


Performance Impact
------------------

None



Other deployer impact
---------------------

In order to utilize new functionality and bay drivers, operators will need
to update their installation and configure bay models to use a driver.


Developer impact
----------------

Due to the significant impact on the current codebase, a phased implementation
approach will be necessary. This is defined in the Work Items section.

Code will be contributed for COE-specific functionality in a new way, and will
need to abide by the new architecture. Documentation and a good first
implementation will play an important role in helping developers contribute
new functionality.


Implementation
==============


Assignee(s)
-----------

Primary assignee:
murali-allada

Other contributors:
jamiehannaford
strigazi


Work Items
----------

1. New ``drivers`` directory

2. Change ``coe`` attribute to ``driver``

3. COE drivers implementation (swarm-fedora, k8s-fedora, k8s-coreos,
   mesos-ubuntu). Templates should remain in directory tree until their
   accompanying driver has been implemented.

4. Delete old conductor files

5. Update client

6. Add documentation

7. Improve user experience for operators of forking/creating new
   drivers. One way we could do this is by creating new client commands or
   scripts. This is orthogonal to this spec, and will be considered after
   its core implementation.

Dependencies
============

None


Testing
=======

Each commit will be accompanied with unit tests, and Tempest functional tests.


Documentation Impact
====================

A set of documentation for this architecture will be required. We should also
provide a developer guide for creating a new bay driver and updating existing
ones.


References
==========

`Using Stevedore in your Application
<http://docs.openstack.org/developer/stevedore/tutorial/index.html/>`_.

.. _stevedore: http://docs.openstack.org/developer/stevedore/
