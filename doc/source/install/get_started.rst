====================================================
Container Infrastructure Management service overview
====================================================

The Container Infrastructure Management service consists of the
following components:

``magnum`` command-line client
  A CLI that communicates with the ``magnum-api`` to create and manage
  container clusters.  End developers can directly use the magnum
  REST API.

``magnum-api`` service
  An OpenStack-native REST API that processes API requests by sending
  them to the ``magnum-conductor`` via AMQP.

``magnum-conductor`` service
  Runs on a controller machine and connects to heat to orchestrate a
  cluster. Additionally, it connects to a Kubernetes API endpoint.
