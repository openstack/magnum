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
