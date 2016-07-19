4. Update heat policy to allow magnum list stacks. Edit your heat policy file,
   usually ``/etc/heat/policy.json``:

   .. code-block:: ini

      ...
      stacks:global_index: "role:admin",

   Now restart heat.
