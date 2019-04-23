A Kubernetes cluster with Heat
==============================

These [Heat][] templates will deploy a [Kubernetes][] cluster that
supports automatic scaling based on CPU load.

[heat]: https://wiki.openstack.org/wiki/Heat
[kubernetes]: https://github.com/GoogleCloudPlatform/kubernetes

The cluster uses [Flannel][] to provide an overlay network connecting
pods deployed on different minions.

[flannel]: https://github.com/coreos/flannel

## Requirements

### Guest image

These templates will work with either openSUSE JeOS or SLES JeOS images
that are prepared for Docker and Kubernetes.

You can enable docker registry v2 by setting the "registry_enabled"
parameter to "true".

## Creating the stack

Creating an environment file `local.yaml` with parameters specific to
your environment:

    parameters:
      ssh_key_name: testkey
      external_network: public
      dns_nameserver: 192.168.200.1
      server_image: openSUSELeap42.1-jeos-k8s
      registry_enabled: true
      registry_username: username
      registry_password: password
      registry_domain: domain
      registry_trust_id: trust_id
      registry_auth_url: auth_url
      registry_region: region
      registry_container: container

And then create the stack, referencing that environment file:

    heat stack-create -f kubecluster.yaml -e local.yaml my-kube-cluster

You must provide values for:

- `ssh_key_name`
- `server_image`

If you enable docker registry v2, you must provide values for:

- `registry_username`
- `registry_password`
- `registry_domain`
- `registry_trust_id`
- `registry_auth_url`
- `registry_region`
- `registry_container

## Interacting with Kubernetes

You can get the ip address of the Kubernetes master using the `heat
output-show` command:

    $ heat output-show my-kube-cluster kube_masters
    "192.168.200.86"

You can ssh into that server as the `minion` user:

    $ ssh minion@192.168.200.86

And once logged in you can run `kubectl`, etc:

    $ kubectl get minions
    NAME                LABELS       STATUS
    10.0.0.4            <none>       Ready

You can log into your minions using the `minion` user as well.  You
can get a list of minion addresses by running:

    $ heat output-show my-kube-cluster kube_minions
    [
      "192.168.200.182"
    ]

You can get the docker registry v2 address:
    $ heat output-show my-kube-cluster registry_address
    localhost:5000

## Testing

The templates install an example Pod and Service description into
`/etc/kubernetes/examples`.  You can deploy this with the following
commands:

    $ kubectl create -f /etc/kubernetes/examples/web.service
    $ kubectl create -f /etc/kubernetes/examples/web.pod

This will deploy a minimal webserver and a service.  You can use
`kubectl get pods` and `kubectl get services` to see the results of
these commands.

## License

Copyright 2016 SUSE Linux GmbH

Licensed under the Apache License, Version 2.0 (the "License");
you may not use these files except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

## Contributing

Please submit bugs and pull requests via the Gerrit repository at
https://review.openstack.org/. For more information, please refer
to the following resources:

* **Documentation:** https://docs.openstack.org/magnum/latest/
* **Source:** https://opendev.org/openstack/magnum
