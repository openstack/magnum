Rolling upgrade is an important feature a user may want for a managed
Kubernetes service.

.. note::

    Kubernetes version upgrade is only supported by the Fedora Atomic and
    the Fedora CoreOS drivers.

A user can run a command as shown below to trigger a rolling ugprade for
Kubernetes version upgrade or node operating system version upgrade.

.. code-block:: bash

    openstack coe cluster upgrade <cluster ID> <new cluster template ID>

The key parameter in the command is the new cluster template ID. For
Kubernetes version upgrade, a newer version for label `kube_tag` should be
provided. Downgrade is not supported.

A simple operating system upgrade can be applied using a new image ID in the
new cluster template. However, this entails a downtime for applications running
on the cluster, because all the nodes will be rebuilt one by one.

The Fedora Atomic driver supports a more gradeful operating system upgrade.
Similar to the Kubernetes version upgrade, it will cordon and drain the nodes
before upgrading the operating system with rpm-ostree command. There are one of
two labels which must be provided to support this feature:

* `ostree_commit`: this is a commit ID of ostree the current system should be
  upgraded to. An example of a commit ID is
  `1766b4526f1a738ba1e6e0a66264139f65340bcc28e7045f10cbe6d161eb1925`,
* `ostree_remote`: this is a remote name of ostree the current system should be
  rebased to. An example of a remote name is
  `fedora-atomic:fedora/29/x86_64/atomic-host`.

If both labels are present, `ostree_commit` takes precedence. To check if there
are updates available, run `sudo rpm-ostree upgrade --check` on the Atomic host
which will show you the latest commit ID that can be upgraded to.
