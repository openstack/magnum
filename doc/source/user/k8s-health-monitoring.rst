Currently Magnum can support health monitoring for Kubernetes cluster. There
are two scenarios supported now: internal and external.

Internal Health Monitoring
--------------------------

Magnum has a periodic job to poll the k8s cluster if it is a reachable cluster.
If the floating IP is enabled, or the master loadbalancer is enabled and the
master loadbalancer has floating IP associated, then Magnum will take this
cluster as reachable. Then Magnum will call the k8s API per 10 seconds to poll
the health status of the cluster and then update the two attributes:
`health_status` and `health_status_reason`.

External Health Montorning
--------------------------

Currently, only `magnum-auto-healer
<https://github.com/kubernetes/cloud-provider-openstack/tree/master/pkg/autohealing>`_
is able to update cluster's `health_status` and `health_status_reason`
attributes. Both the label `auto_healing_enabled=True` and
`auto_healing_controller=magnum-auto-healer` must be set, otherwise, the two
attributes' value will be overwritten with 'UNKNOWN' and 'The cluster is not
accessible'. The health_status attribute can either be in `HEALTHY`,
`UNHEALTHY` or `UNKNOWN` and the health_status_reason is a dictionary
of the hostnames and their current health statuses and the API health status.

