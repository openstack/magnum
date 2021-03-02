step="enable-node-problem-detector"
printf "Starting to run ${step}\n"

. /etc/sysconfig/heat-params

_gcr_prefix=${CONTAINER_INFRA_PREFIX:-k8s.gcr.io/}

# Either auto scaling or auto healing we need CA to be deployed
if [[ "$(echo $AUTO_HEALING_ENABLED | tr '[:upper:]' '[:lower:]')" = "true" || "$(echo $NPD_ENABLED | tr '[:upper:]' '[:lower:]')" = "true" ]]; then
    # Generate Node Problem Detector manifest file
    NPD_DEPLOY=/srv/magnum/kubernetes/manifests/npd.yaml

    [ -f ${NPD_DEPLOY} ] || {
        echo "Writing File: $NPD_DEPLOY"
        mkdir -p $(dirname ${NPD_DEPLOY})
        cat << EOF > ${NPD_DEPLOY}
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: node-problem-detector
  namespace: kube-system
  labels:
    kubernetes.io/cluster-service: "true"
    addonmanager.kubernetes.io/mode: Reconcile
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: magnum:podsecuritypolicy:node-problem-detector
  namespace: kube-system
  labels:
    addonmanager.kubernetes.io/mode: Reconcile
    kubernetes.io/cluster-service: "true"
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: magnum:podsecuritypolicy:privileged
subjects:
- kind: ServiceAccount
  name: node-problem-detector
  namespace: kube-system
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: npd-binding
  labels:
    kubernetes.io/cluster-service: "true"
    addonmanager.kubernetes.io/mode: Reconcile
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: system:node-problem-detector
subjects:
- kind: ServiceAccount
  name: node-problem-detector
  namespace: kube-system
---
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: npd
  namespace: kube-system
  labels:
    k8s-app: node-problem-detector
    version: ${NODE_PROBLEM_DETECTOR_TAG}
    kubernetes.io/cluster-service: "true"
    addonmanager.kubernetes.io/mode: Reconcile
spec:
  selector:
    matchLabels:
      k8s-app: node-problem-detector
      version: ${NODE_PROBLEM_DETECTOR_TAG}
  template:
    metadata:
      labels:
        k8s-app: node-problem-detector
        version: ${NODE_PROBLEM_DETECTOR_TAG}
        kubernetes.io/cluster-service: "true"
    spec:
      containers:
      - name: node-problem-detector
        image: ${_gcr_prefix}node-problem-detector:${NODE_PROBLEM_DETECTOR_TAG}
        command:
        - "/bin/sh"
        - "-c"
        # Pass both config to support both journald and syslog.
        - "exec /node-problem-detector --logtostderr --system-log-monitors=/config/kernel-monitor.json,/config/kernel-monitor-filelog.json,/config/docker-monitor.json,/config/docker-monitor-filelog.json 2>&1 | tee /var/log/node-problem-detector.log"
        securityContext:
          privileged: true
        resources:
          limits:
            cpu: "200m"
            memory: "100Mi"
          requests:
            cpu: "20m"
            memory: "20Mi"
        env:
        - name: NODE_NAME
          valueFrom:
            fieldRef:
              fieldPath: spec.nodeName
        volumeMounts:
        - name: log
          mountPath: /var/log
        - name: localtime
          mountPath: /etc/localtime
          readOnly: true
      volumes:
      - name: log
        hostPath:
          path: /var/log/
      - name: localtime
        hostPath:
          path: /etc/localtime
          type: "FileOrCreate"
      serviceAccountName: node-problem-detector
      tolerations:
      - operator: "Exists"
        effect: "NoExecute"
      - key: "CriticalAddonsOnly"
        operator: "Exists"
EOF
    }

    echo "Waiting for Kubernetes API..."
    until  [ "ok" = "$(kubectl get --raw='/healthz')" ]
    do
        sleep 5
    done

    kubectl apply -f ${NPD_DEPLOY}

    printf "Finished running ${step}\n"
fi


function enable_draino {
    echo "Installing draino"
    _docker_draino_prefix=${CONTAINER_INFRA_PREFIX:-docker.io/planetlabs/}
    draino_manifest=/srv/magnum/kubernetes/manifests/draino.yaml

    [ -f ${draino_manifest} ] || {
        echo "Writing File: $draino_manifest"
        mkdir -p $(dirname ${draino_manifest})
        cat << EOF > ${draino_manifest}
---
apiVersion: v1
kind: ServiceAccount
metadata:
  labels: {component: draino}
  name: draino
  namespace: kube-system
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  labels: {component: draino}
  name: draino
rules:
- apiGroups: ['']
  resources: [events]
  verbs: [create, patch, update]
- apiGroups: ['']
  resources: [nodes]
  verbs: [get, watch, list, update]
- apiGroups: ['']
  resources: [nodes/status]
  verbs: [patch]
- apiGroups: ['']
  resources: [pods]
  verbs: [get, watch, list]
- apiGroups: ['']
  resources: [pods/eviction]
  verbs: [create]
- apiGroups: [extensions]
  resources: [daemonsets]
  verbs: [get, watch, list]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  labels: {component: draino}
  name: draino
roleRef: {apiGroup: rbac.authorization.k8s.io, kind: ClusterRole, name: draino}
subjects:
- {kind: ServiceAccount, name: draino, namespace: kube-system}
---
apiVersion: apps/v1
kind: Deployment
metadata:
  labels: {component: draino}
  name: draino
  namespace: kube-system
spec:
  # Draino does not currently support locking/master election, so you should
  # only run one draino at a time. Draino won't start draining nodes immediately
  # so it's usually safe for multiple drainos to exist for a brief period of
  # time.
  replicas: 1
  selector:
    matchLabels: {component: draino}
  template:
    metadata:
      labels: {component: draino}
      name: draino
      namespace: kube-system
    spec:
      nodeSelector:
        node-role.kubernetes.io/master: ""
      hostNetwork: true
      tolerations:
        - effect: NoSchedule
          operator: Exists
        - key: CriticalAddonsOnly
          operator: Exists
        - effect: NoExecute
          operator: Exists
        - key: node.cloudprovider.kubernetes.io/uninitialized
          value: "true"
          effect: NoSchedule
        - key: node-role.kubernetes.io/master
          effect: NoSchedule
      containers:
      # You'll want to change these labels and conditions to suit your deployment.
      - command: [/draino, --node-label=draino-enabled=true, --evict-daemonset-pods, --evict-emptydir-pods, NotReady]
        image: ${_docker_draino_prefix}draino:${DRAINO_TAG}
        livenessProbe:
          httpGet: {path: /healthz, port: 10002}
          initialDelaySeconds: 30
        name: draino
      serviceAccountName: draino
EOF
    }

    kubectl apply -f ${draino_manifest}
}

function enable_magnum_auto_healer {
    echo "Installing magnum_auto_healer"
    image_prefix=${CONTAINER_INFRA_PREFIX:-docker.io/k8scloudprovider/}
    image_prefix=${image_prefix%/}
    magnum_auto_healer_manifest=/srv/magnum/kubernetes/manifests/magnum_auto_healer.yaml

    [ -f ${magnum_auto_healer_manifest} ] || {
        echo "Writing File: ${magnum_auto_healer_manifest}"
        mkdir -p $(dirname ${magnum_auto_healer_manifest})
        cat << EOF > ${magnum_auto_healer_manifest}
---
kind: ServiceAccount
apiVersion: v1
metadata:
  name: magnum-auto-healer
  namespace: kube-system

---
kind: ClusterRoleBinding
apiVersion: rbac.authorization.k8s.io/v1
metadata:
  name: magnum-auto-healer
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: cluster-admin
subjects:
  - kind: ServiceAccount
    name: magnum-auto-healer
    namespace: kube-system

---
kind: ConfigMap
apiVersion: v1
metadata:
  name: magnum-auto-healer-config
  namespace: kube-system
data:
  config.yaml: |
    cluster-name: ${CLUSTER_UUID}
    dry-run: false
    monitor-interval: 30s
    check-delay-after-add: 20m
    leader-elect: true
    healthcheck:
      master:
        - type: Endpoint
          params:
            unhealthy-duration: 3m
            protocol: HTTPS
            port: 6443
            endpoints: ["/healthz"]
            ok-codes: [200]
        - type: NodeCondition
          params:
            unhealthy-duration: 3m
            types: ["Ready"]
            ok-values: ["True"]
      worker:
        - type: NodeCondition
          params:
            unhealthy-duration: 3m
            types: ["Ready"]
            ok-values: ["True"]
    openstack:
      auth-url: ${AUTH_URL}
      user-id: ${TRUSTEE_USER_ID}
      password: ${TRUSTEE_PASSWORD}
      trust-id: ${TRUST_ID}
      region: ${REGION_NAME}
      ca-file: /etc/kubernetes/ca-bundle.crt

---
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: magnum-auto-healer
  namespace: kube-system
  labels:
    k8s-app: magnum-auto-healer
spec:
  selector:
    matchLabels:
      k8s-app: magnum-auto-healer
  template:
    metadata:
      labels:
        k8s-app: magnum-auto-healer
    spec:
      hostNetwork: true
      serviceAccountName: magnum-auto-healer
      tolerations:
        - effect: NoSchedule
          operator: Exists
        - key: CriticalAddonsOnly
          operator: Exists
        - effect: NoExecute
          operator: Exists
      nodeSelector:
        node-role.kubernetes.io/master: ""
      containers:
        - name: magnum-auto-healer
          image: ${image_prefix}/magnum-auto-healer:${MAGNUM_AUTO_HEALER_TAG}
          imagePullPolicy: Always
          args:
            - /bin/magnum-auto-healer
            - --config=/etc/magnum-auto-healer/config.yaml
            - --v
            - "2"
          volumeMounts:
            - name: config
              mountPath: /etc/magnum-auto-healer
            - name: kubernetes-config
              mountPath: /etc/kubernetes
              readOnly: true
      volumes:
        - name: config
          configMap:
            name: magnum-auto-healer-config
        - name: kubernetes-config
          hostPath:
            path: /etc/kubernetes
EOF
    }

    kubectl apply -f ${magnum_auto_healer_manifest}
}

step="enable-auto-healing"
printf "Starting to run ${step}\n"

if [ "$(echo $AUTO_HEALING_ENABLED | tr '[:upper:]' '[:lower:]')" = "true" ]; then
    autohealing_controller=$(echo ${AUTO_HEALING_CONTROLLER} | tr '[:upper:]' '[:lower:]')
    case "${autohealing_controller}" in
    "")
        echo "No autohealing controller configured."
        ;;
    "draino")
        enable_draino
        ;;
    "magnum-auto-healer")
        enable_magnum_auto_healer
        ;;
    *)
        echo "Autohealing controller ${autohealing_controller} not supported."
        ;;
    esac
fi

printf "Finished running ${step}\n"
