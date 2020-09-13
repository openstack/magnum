Currently, there are several ways to access the Kubernetes API, such as RBAC,
ABAC, Webhook, etc. Though RBAC is the best way for most of the cases, Webhook
provides a good approach for Kubernetes to query an outside REST service when
determining user privileges. In other words, we can use a Webhook to integrate
other IAM service into Kubernetes. In our case, under the OpenStack context,
we're introducing the intergration with Keystone auth for Kubernetes.

Since Rocky release, we introduced a new label named `keystone_auth_enabled`,
by default it's True, which means user can get this very nice feature out of
box.

Create roles
------------

As cloud provider, necessary Keystone roles for Kubernetes cluster operations
need to be created for different users, e.g. k8s_admin, k8s_developer,
k8s_viewer

- k8s_admin role can create/update/delete Kubernetes cluster, can also
  associate roles to other normal users within the tenant
- k8s_developer can create/update/delete/watch Kubernetes cluster resources
- k8s_viewer can only have read access to Kubernetes cluster resources

NOTE: Those roles will be created automatically in devstack. Below is the
samples commands about how to create them.

.. code-block:: bash

  source ~/openstack_admin_credentials
  for role in "k8s_admin" "k8s_developer" "k8s_viewer"; do openstack role create $role; done

  openstack user create demo_viewer --project demo --password password
  openstack role add --user demo_viewer --project demo k8s_viewer

  openstack user create demo_editor --project demo --password password
  openstack role add --user demo_developer --project demo k8s_developer

  openstack user create demo_admin --project demo --password password
  openstack role add --user demo_admin --project demo k8s_admin

Those roles should be public and can be accessed by any project so that user
can configure their cluster's role policies with those roles.

Setup configmap for authorization policies
------------------------------------------

While the `k8s-keystone-auth` service is enabled in clusters by default, users
will need specify their own authorization policy to start making use of this
feature.

The user can specify their own authorization policy by either:

- Updating the placeholder `k8s-keystone-auth-policy` configmap, created
  by default in the `kube-system` namespace. This does not require restarting
  the `k8s-keystone-auth` service.
- Reading the policy from a default policy file. In devstack the policy file is
  created automatically.

Currently, the `k8s-keystone-auth` service supports four types of policies:

- user. The Keystone user ID or name.
- project. The Keystone project ID or name.
- role. The user role defined in Keystone.
- group. The group is not a Keystone concept actually, it’s supported for
  backward compatibility, you can use group as project ID.

For example, if we wish to configure a policy to only allow the users in
project `demo` with `k8s-viewer` role in OpenStack to query the pod information
from all the namespaces, then we can update the default
`k8s-keystone-auth-policy` configmap as follows.

.. code-block:: bash

    cat <<EOF | kubectl apply -f -
    apiVersion: v1
    kind: ConfigMap
    metadata:
    name: k8s-keystone-auth-policy
    namespace: kube-system
    data:
    policies: |
        [
        {
            "resource": {
            "verbs": ["get", "list", "watch"],
            "resources": ["pods"],
            "version": "*",
            "namespace": "default"
            },
            "match": [
            {
                "type": "role",
                "values": ["k8s-viewer"]
            },
            {
                "type": "project",
                "values": ["demo"]
            }
            ]
        }
        ]
    EOF

More on keystone authorization policies can be found in the
kubernetes/cloud-provider-openstack documentation for
`Using the Keystone Webhook Authenticator and Authorizer
<https://github.com/kubernetes/cloud-provider-openstack/blob/master/docs/using-keystone-webhook-authenticator-and-authorizer.md#prepare-the-authorization-policy-optional>`_

Note: If the user wishes to use an alternate name for the
`k8s-keystone-auth-policy` configmap they will need to update the value of the
`--policy-configmap-name` parameter passed to the `k8s-keystone-auth` service
and then restart the service.

Next the user needs to get a token from Keystone to have a kubeconfig for
kubectl. The user can also get the config with Magnum python client.

Here is a sample of the kubeconfig:

.. code-block:: bash

    apiVersion: v1
    clusters:
    - cluster:
        certificate-authority-data: CERT-DATA==
        server: https://172.24.4.25:6443
    name: k8s-2
    contexts:
    - context:
        cluster: k8s-2
        user: openstackuser
    name: openstackuser@kubernetes
    current-context: openstackuser@kubernetes
    kind: Config
    preferences: {}
    users:
    - name: openstackuser
    user:
        exec:
        command: /bin/bash
        apiVersion: client.authentication.k8s.io/v1alpha1
        args:
        - -c
        - >
            if [ -z ${OS_TOKEN} ]; then
                echo 'Error: Missing OpenStack credential from environment variable $OS_TOKEN' > /dev/stderr
                exit 1
            else
                echo '{ "apiVersion": "client.authentication.k8s.io/v1alpha1", "kind": "ExecCredential", "status": { "token": "'"${OS_TOKEN}"'"}}'
            fi

After exporting the Keystone token to the ``OS_TOKEN`` environment variable,
the user should be able to list pods with `kubectl`.

Setup configmap for role synchronization policies
-------------------------------------------------

To start taking advantage of role synchronization between kubernetes and openstack
users need to specify an `authentication synchronization policy
<https://github.com/kubernetes/cloud-provider-openstack/blob/master/docs/using-auth-data-synchronization.md#example-of-sync-config-file>`_

Users can specify their own policy by either:

- Updating the placeholder `keystone-sync-policy` configmap, created by
  default in the `kube-system` namespace. This does *not* require restarting
  `k8s-keystone-auth`
- Reading the policy from a local config file. This requires restarting the
  `k8s-keystone-auth` service.

For example, to set a policy which assigns the `project-1` group in
kubernetes to users who have been assigned the `member` role in Keystone the
user can update the default `keystone-sync-policy` configmap as follows.

.. code-block:: bash

    cat <<EOF | kubectl apply -f -
    apiVersion: v1
    kind: ConfigMap
    metadata:
      name: keystone-sync-policy
      namespace: kube-system
    data:
      syncConfig: |
        role-mappings:
          - keystone-role: member
            groups: ["project-1"]
    EOF

If users wish to use an alternative name for the keystone-sync-policy
configmap they will need to update the value of the ``--sync-configmap-name``
parameter passed to the `k8s-keystone-auth` service and then restart service.

For more examples and information on configuring and using authorization
synchronization policies please refer to the
kubernetes/cloud-provider-openstack documentation for `Authentication
synchronization between Keystone and Kubernetes
<https://github.com/kubernetes/cloud-provider-openstack/blob/master/docs/using-auth-data-synchronization.md>`_
