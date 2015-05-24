A Kubernetes cluster with Heat
==============================

These [Heat][] templates will deploy an *N*-node [Kubernetes][] cluster,
where *N* is the value of the `number_of_minions` parameter you
specify when creating the stack.

[heat]: https://wiki.openstack.org/wiki/Heat
[kubernetes]: https://github.com/GoogleCloudPlatform/kubernetes

The cluster uses [Flannel][] to provide an overlay network connecting
pods deployed on different minions.

[flannel]: https://github.com/coreos/flannel

## Requirements

### OpenStack

These templates will work with the Juno version of Heat.

### Guest image

These templates will work with either CentOS Atomic Host or Fedora 21
Atomic.

You can enable the VXLAN backend for flannel by setting the
"flannel_use_vxlan" parameter to "true", but I have run into kernel
crashes using that backend with CentOS 7.  It seems to work fine with
Fedora 21.

## Creating the stack

Creating an environment file `local.yaml` with parameters specific to
your environment:

    parameters:
      ssh_key_name: lars
      external_network: public
      dns_nameserver: 192.168.200.1
      server_image: centos-7-atomic-20150101

And then create the stack, referencing that environment file:

    heat stack-create -f kubecluster.yaml -e local.yaml my-kube-cluster

You must provide values for:

- `ssh_key_name`
- `external_network`
- `server_image`

## Interacting with Kubernetes

You can get the ip address of the Kubernetes master using the `heat
output-show` command:

    $ heat output-show my-kube-cluster kube_master
    "192.168.200.86"

You can ssh into that server as the `minion` user:

    $ ssh minion@192.168.200.86

And once logged in you can run `kubectl`, etc:

    $ kubectl get minions
    NAME                LABELS       STATUS
    10.0.0.4            <none>       Ready

You can log into your minions using the `minion` user as well.  You
can get a list of minion addresses by running:

    $ heat output-show my-kube-cluster kube_minions_external
    [
      "192.168.200.182"
    ]

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

Copyright 2014 Lars Kellogg-Stedman <lars@redhat.com>

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

Please submit bugs and pull requests via the [GitHub repository][] at
https://github.com/larsks/heat-kubernetes/.

When submitting pull requests:

- Please ensure that each pull request contains a single commit and
  contains only related changes.  Put unrelated changes in multiple
  pull requests.

- Please avoid conflating new features with
  stylistic/formatting/cleanup changes.

[github repository]: https://github.com/larsks/heat-kubernetes/

