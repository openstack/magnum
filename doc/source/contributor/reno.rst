Release Notes
=============

What is reno ?
--------------

Magnum uses `reno <https://docs.openstack.org/reno/latest/index.html>`_ for
providing release notes in-tree. That means that a patch can include a *reno
file* or a series can have a follow-on change containing that file explaining
what the impact is.

A *reno file* is a YAML file written in the releasenotes/notes tree which is
generated using the reno tool this way:

.. code-block:: bash

  $ tox -e venv -- reno new <name-your-file>

where usually ``<name-your-file>`` can be ``bp-<blueprint_name>`` for a
blueprint or ``bug-XXXXXX`` for a bugfix.

Refer to the `reno documentation <https://docs.openstack.org/reno/latest/user/usage.html#editing-a-release-note>`_
for the full list of sections.


When a release note is needed
-----------------------------

A release note is required anytime a reno section is needed. Below are some
examples for each section. Any sections that would be blank should be left out
of the note file entirely. If no section is needed, then you know you don't
need to provide a release note :-)

* ``upgrade``
    * The patch has an `UpgradeImpact <https://docs.openstack.org/infra/manual/developers.html#peer-review>`_ tag
    * A DB change needs some deployer modification (like a migration)
    * A configuration option change (deprecation, removal or modified default)
    * some specific changes that have a `DocImpact <https://docs.openstack.org/infra/manual/developers.html#peer-review>`_ tag
      but require further action from an deployer perspective
    * any patch that requires an action from the deployer in general

* ``security``
    * If the patch fixes a known vulnerability

* ``features``
    * If the patch has an `APIImpact <https://docs.openstack.org/infra/manual/developers.html#peer-review>`_ tag

* ``critical``
    * Bugfixes categorized as Critical in Launchpad *impacting users*

* ``fixes``
    * No clear definition of such bugfixes. Hairy long-standing bugs with high
      importance that have been fixed are good candidates though.


Three sections are left intentionally unexplained (``prelude``, ``issues`` and
``other``). Those are targeted to be filled in close to the release time for
providing details about the soon-ish release. Don't use them unless you know
exactly what you are doing.
