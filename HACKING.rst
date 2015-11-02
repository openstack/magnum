Magnum Style Commandments
=========================

- Step 1: Read the OpenStack Style Commandments
  http://docs.openstack.org/developer/hacking/
- Step 2: Read on

Magnum Specific Commandments
----------------------------

- [M301] policy.enforce_wsgi decorator must be the first decorator on a method.
- [M318] Change assertEqual(A, None) or assertEqual(None, A) by optimal assert
  like assertIsNone(A)
- [M322] Method's default argument shouldn't be mutable.
- [M323] Change assertEqual(True, A) or assertEqual(False, A) by optimal assert
  like assertTrue(A) or assertFalse(A)
- [M302] Change assertEqual(A is not None) by optimal assert like
  assertIsNotNone(A).
- [M316] Change assertTrue(isinstance(A, B)) by optimal assert like
  assertIsInstance(A, B).
