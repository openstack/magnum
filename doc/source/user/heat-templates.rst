Heat Stack Templates are what Magnum passes to Heat to generate a cluster. For
each ClusterTemplate resource in Magnum, a Heat stack is created to arrange all
of the cloud resources needed to support the container orchestration
environment. These Heat stack templates provide a mapping of Magnum object
attributes to Heat template parameters, along with Magnum consumable stack
outputs. Magnum passes the Heat Stack Template to the Heat service to create a
Heat stack. The result is a full Container Orchestration Environment.

.. list-plugins:: magnum.template_definitions
   :detailed:
