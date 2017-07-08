Magnum Style Commandments
=========================

- Step 1: Read the OpenStack Style Commandments
  http://docs.openstack.org/developer/hacking/
- Step 2: Read on

Magnum Specific Commandments
----------------------------

- [M302] Change assertEqual(A is not None) by optimal assert like
  assertIsNotNone(A).
- [M310] timeutils.utcnow() wrapper must be used instead of direct calls to
  datetime.datetime.utcnow() to make it easy to override its return value.
- [M316] Change assertTrue(isinstance(A, B)) by optimal assert like
  assertIsInstance(A, B).
- [M322] Method's default argument shouldn't be mutable.
- [M336] Must use a dict comprehension instead of a dict constructor
  with a sequence of key-value pairs.
- [M338] Use assertIn/NotIn(A, B) rather than assertEqual(A in B, True/False).
- [M339] Don't use xrange()
- [M340] Check for explicit import of the _ function.
- [M352] LOG.warn is deprecated. Enforce use of LOG.warning.
- [M353] String interpolation should be delayed at logging calls.
