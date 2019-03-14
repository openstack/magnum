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

Given the k8s Keystone auth has been enable by default, user can get the
authentication support by default without doing anything. However, user can't
do anything actually before setup a default authorization policies.

The authorization policy can be specified using an existing configmap name in
the cluster, by doing this, the policy could be changed dynamically without
the k8s-keystone-auth service restart.

Or the policy can be read from a default policy file. In devstack, the policy
file will be created automatically.

Currently, k8s-keystone-auth service supports four types of policies:

- user. The Keystone user ID or name.
- roject. The Keystone project ID or name.
- role. The user role defined in Keystone.
- group. The group is not a Keystone concept actually, it’s supported for
  backward compatibility, you can use group as project ID.

For example, in the following configmap, we only allow the users in
project demo with k8s-viewer role in OpenStack to query the pod information
from all the namespaces. So we need to update the configmap
`k8s-keystone-auth-policy` which has been created in kube-system namespace.

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

Please note that the default configmap name is `k8s-keystone-auth-policy`, user
can change it, but they have to change the config of the k8s keystone auth
service configuration as well and restart the service.

Now user need to get a token from Keystone to have a kubeconfig for kubectl,
user can also get the config with Magnum python client.

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

Now after export the Keystone token to OS_TOKEN, user should be able to list
pods with kubectl.
