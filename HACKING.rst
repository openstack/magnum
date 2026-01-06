Magnum Style Commandments
=========================

- Step 1: Read the OpenStack Style Commandments
  https://docs.openstack.org/hacking/latest/
- Step 2: Read on

Magnum Specific Commandments
----------------------------

- [M310] timeutils.utcnow() wrapper must be used instead of direct calls to
  datetime.datetime.utcnow() to make it easy to override its return value.
- [M322] Method's default argument shouldn't be mutable.
- [M336] Must use a dict comprehension instead of a dict constructor
  with a sequence of key-value pairs.
- [M340] Check for explicit import of the _ function.
- [M352] LOG.warn is deprecated. Enforce use of LOG.warning.
