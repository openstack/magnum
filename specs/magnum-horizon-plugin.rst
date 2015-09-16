..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

===================================
Web Interface for Magnum in Horizon
===================================

Launchpad blueprint:

https://blueprints.launchpad.net/magnum/+spec/magnum-horizon-plugin

Currently there is no way for a user to interact with Magnum through a web
based user interface, as they are used to doing with other OpenStack
components. This implementation aims to introduce this interface as an
extension of Horizon (the OpenStack Dashboard) and expose all the features of
Magnum in a way familiar to users.

Problem description
===================

In order to increase adoption and usability of Magnum we need to introduce a UI
component for users and administrators to interact with Magnum without the need
to use the command line. The UI proposed to be built will model all of the
features currently available in the Magnum REST API and built using the Horizon
plugin architecture to remain in line with other OpenStack UI projects and
minimise the amount of new code that needs to be added.

Use Cases
----------
1. An end user wanting to use Magnum with OpenStack who is not comfortable in
   issuing commands with the python client will use the web user interface to
   interact with Magnum.
2. An administrator may use the user interface to provide a quick overview of
   what Magnum has deployed in their OpenStack environment.

Proposed change
===============

The first step will be to extend the Horizon API to include CRUD operations
that are needed to interact with Magnum. Assuming that there are no issues here
and API changes/additions are not required to Magnum, we can begin to
design/implement the interface. We will aim to minimize the amount of Magnum
specific UI code that will need to be maintained by reusing components from
Horizon. This will also speed up the development significantly.

It is suggested the initial implementation of Magnum UI will include basic CRUD
operations on BayModel and Bay resources. This will be the starting point for
development and upon completion this will represent version 1.

Future direction includes adding CRUD operations for other Magnum features
(Pod, Container, Service, ReplicationController) and will be tracked by new
blueprints as they represent significant additional effort. The ultimate goal,
a user should be able to perform all normal interactions with Magnum through
the UI with no need for interaction with the python client.

Suggestions for further improvement include visualising Magnum resources to
provide a quick overview of how resources are deployed.

Bugs/Blueprints relating specifically to the Magnum UI will be tracked here:

https://launchpad.net/magnum-ui

Mockups/Designs will be shared using the OpenStack Invision account located
here:

https://openstack.invisionapp.com

Alternatives
------------

One alternative to this approach is to develop an entirely separate UI
specifically for Magnum. We will not use this approach as it does not fall in
line with how other projects are managing their user interfaces and this
approach would ultimately result in a significantly larger effort with much
duplication with Horizon.

Data model impact
-----------------

None

REST API impact
---------------

For Magnum, none. The Horizon API will need to be extended to include Create,
Read, Update, Delete operations for all features available in the Magnum REST
API. However, this extension to the Horizon API will live in the Magnum UI tree
not the upstream Horizon tree.

Security impact
---------------

None

Notifications impact
--------------------

None

Other end user impact
---------------------

None

Performance Impact
------------------

The Magnum API will be called from the user interface to return information to
the user about the current state of Magnum objects and perform new interactions
with Magnum. For every action a user performs from the user interface at least
one API call to Magnum will need to be made.

Other deployer impact
---------------------

As the Magnum user interface will be managed and stored outside of the Horizon
project deployers will need to pull down the Magnum UI code and add this to
their Horizon install.

In order to add the Magnum UI to Horizon the deployer will have to copy an
enable file to openstack_dashboard/local/enabled/ in their Horizon directory
and then run Horizon as they would normally.

Developer impact
----------------

None

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  bradjones

Work Items
----------

1. Extend Horizon API in include Magnum calls
2. CRUD operations on BayModel and Bay resources
3. CRUD operations on other Magnum features (Pod, Container, Service, etc.)
4. Refine the user experience

Dependencies
============

None

Testing
=======

Each commit will be accompanied with unit tests. There will also be functional
tests which will be used as part of a cross-functional gate test for Magnum.
This additional gate test will be non-voting as failures will not indicate
issues with Magnum but instead serves as advanced warning of any changes that
could potentially break the UI.

Documentation Impact
====================

An installation guide will be required.

References
==========

None
