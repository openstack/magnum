Developer Troubleshooting Guide
================================

This guide is intended to provide information on how to resolve common
problems encountered when developing code for magnum.

Troubleshooting MySQL
-----------------------

When creating alembic migrations, developers might encounter the ``Multiple
head revisions are present for given argument 'head'`` error.

This can occur when two migrations revise the same head.  For example, the
developer creates a migration locally but another migration has already been
accepted and merged into master that revises the same head::

      $ alembic heads
      12345 (your local head)
      67890 (new master head)

In order to fix this, the developer should update the down_revision of their
local migration to point to the head of the new migration in master::

      # revision identifiers, used by Alembic.
      revision = '12345'
      down_revision = '67890'

Now the newest local migration should be head::

      $ alembic heads
      12345 (your local head)
