.. _monitoring:

Container Monitoring in Kubernetes
----------------------------------

The current monitoring capabilities that can be deployed with magnum span
through different components. These are:

* **metrics-server:** is responsible for the API metrics.k8s.io requests. This
  includes the most basic functionality when using simple HPA metrics or when
  using the *kubectl top* command.

* **prometheus:** is a full fledged service that allows the user to access
  advanced metrics capabilities. These metrics are collected with a resolution
  of 30 seconds and include resources such as CPU, Memory, Disk and Network IO
  as well as R/W rates. These metrics of fine granularity are available on your
  cluster for up to a period of 14 days (default).

* **prometheus-adapter:** is an extra component that integrates with the
  prometheus service and allows a user to create more sophisticated `HPA
  <https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/>`_
  rules. The service integrates fully with the metrics.k8s.io API but at this
  time only custom.metrics.k8s.io is being actively used.


The installation of these services is controlled with the following labels:

_`metrics_server_enabled`
  metrics_server_enabled is used to enable disable the installation of
  the metrics server.
  To use this service tiller_enabled must be true when using
  helm_client_tag<v3.0.0.
  Train default: true
  Stein default: true

_`monitoring_enabled`
  Enable installation of cluster monitoring solution provided by the
  stable/prometheus-operator helm chart.
  To use this service tiller_enabled must be true when using
  helm_client_tag<v3.0.0.
  Default: false

_`prometheus_adapter_enabled`
  Enable installation of cluster custom metrics provided by the
  stable/prometheus-adapter helm chart. This service depends on
  monitoring_enabled.
  Default: true

To control deployed versions, extra labels are available:

_`metrics_server_chart_tag`
  Add metrics_server_chart_tag to select the version of the
  stable/metrics-server chart to install.
  Ussuri default: v2.8.8
  Yoga default: v3.7.0

_`prometheus_operator_chart_tag`
  Add prometheus_operator_chart_tag to select version of the
  stable/prometheus-operator chart to install. When installing the chart,
  helm will use the default values of the tag defined and overwrite them based
  on the prometheus-operator-config ConfigMap currently defined. You must
  certify that the versions are compatible.

_`prometheus_adapter_chart_tag`
  The stable/prometheus-adapter helm chart version to use.
  Train-default: 1.4.0

Full fledged cluster monitoring
+++++++++++++++++++++++++++++++

The prometheus installation provided with the `monitoring_enabled`_ label is in
fact a multi component service. This installation is managed with the
prometheus-operator helm chart and the constituent components are:

* **prometheus** (data collection, storage and search)

  * **node-exporter** (data source for the kubelet/node)
  * **kube-state-metrics** (data source for the running kubernetes objects
    {deployments, pods, nodes, etc})

* **alertmanager** (alarm aggregation, processing and dispatch)
* **grafana** (metrics visualization)


These components are installed in a generic way that makes it easy to have a
cluster wide monitoring infrastructure running with no effort.

.. warning::

    The existent monitoring infra does not take into account the existence of
    nodegroups. If you plan to use nodegroups in your cluster you can take into
    account the maximum number of total nodes and use *max_node_count* to
    correctly setup the prometheus server.

.. note::

    Before creating your cluster take into account the scale of the cluster.
    This is important as the Prometheus server pod might not fit your nodes.
    This is particularly important if you are using *Cluster Autoscaling* as
    the Prometheus server will schedule resources needed to meet the maximum
    number of nodes that your cluster can scale up to defined by
    label (if existent) *max_node_count*.

    The Prometheus server will consume the following resources:

    ::

        RAM:: 256 (base) + Nodes * 40 [MB]
        CPU:: 128 (base) + Nodes * 7 [mCPU]
        Disk:: 15 GB for 2 weeks (depends on usage)


Tuning parameters
+++++++++++++++++

The existent setup configurations allows you to tune the metric infrastructure
to your requisites. Below is a list of labels that can be used for specific
cases:

_`grafana_admin_passwd`
  This label lets users create their own *admin* user password for the Grafana
  interface. It expects a string value.
  Default: admin

_`monitoring_retention_days`
  This label lets users specify the maximum retention time for data collected
  in the prometheus server in days.
  Default: 14

_`monitoring_interval_seconds`
  This label lets users specify the time between metric samples in seconds.
  Default: 30

_`monitoring_retention_size`
  This label lets users specify the maximum size (in gigibytes) for data
  stored by the prometheus server. This label must be used together with
  `monitoring_storage_class_name`_.
  Default: 14

_`monitoring_storage_class_name`
  The kubernetes storage class name to use for the prometheus pvc.
  Using this label will activate the usage of a pvc instead of local
  disk space.
  When using monitoring_storage_class_name 2 pvcs will be created.
  One for the prometheus server which size is set by
  `monitoring_retention_size`_ and one for grafana which is fixed at 1Gi.
  Default: ""

_`monitoring_ingress_enabled`
  This label set's up all the underlying services to be accessible in a
  'route by path' way. This means that the services will be exposed as:

  ::

      my.domain.com/alertmanager
      my.domain.com/prometheus
      my.domain.com/grafana


  This label must be used together with `cluster_root_domain_name`_.
  Default: false

_`cluster_root_domain_name`
  The root domain name to use for the cluster automatically set up
  applications.
  Default: "localhost"

_`cluster_basic_auth_secret`
  The kubernetes secret to use for the proxy basic auth username and password
  for the unprotected services {alertmanager,prometheus}. Basic auth is only
  set up if this file is specified.
  The secret must be in the same namespace as the used proxy (kube-system).
  Default: ""

  ::

    To create this secret you can do:
    $ htpasswd -c auth foo
    $ kubectl create secret generic basic-auth --from-file=auth

_`prometheus_adapter_configmap`
  The name of the prometheus-adapter rules ConfigMap to use. Using this label
  will overwrite the default rules.
  Default: ""
