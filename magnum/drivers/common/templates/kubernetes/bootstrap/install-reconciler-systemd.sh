#!/bin/bash

set -eu

ssh_cmd="ssh -F /srv/magnum/.ssh/config root@localhost"

echo "Installing reconciler systemd units"

cat <<'EOF' | $ssh_cmd "cat > /etc/systemd/system/magnum-reconcile.service.tmp"
[Unit]
Description=Magnum Reconcile
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
ExecStart=/usr/local/bin/magnum-reconcile-launcher run-once
User=root
Group=root
# Backstop above the reconciler's own RECONCILER_RUN_TIMEOUT_SECONDS (default
# 4800s). oneshot units have no start timeout by default, so a run that ignores
# its own context (stuck in a syscall, unkillable wait) would otherwise hold the
# reconcile flock indefinitely and wedge every subsequent run. On timeout
# systemd sends SIGTERM (graceful unwind, lock released on exit) then SIGKILL
# after TimeoutStopSec.
TimeoutStartSec=5100
TimeoutStopSec=120
KillMode=mixed
KillSignal=SIGTERM

# Cgroup memory backstop. kube-apiserver/etcd/controller/kubelet run as their own
# systemd services (separate cgroups), so capping the reconciler tree here keeps
# a runaway Pulumi/Helm run from starving the control plane into a node-wide OOM.
# MemoryHigh is a soft limit: the kernel throttles + reclaims as the cgroup nears
# it rather than killing. 60% of RAM leaves comfortable headroom once parallelism
# and GOMEMLIMIT (set by the launcher) keep steady-state usage well below this.
MemoryAccounting=yes
MemoryHigh=60%

[Install]
WantedBy=multi-user.target
EOF

cat <<'EOF' | $ssh_cmd "cat > /etc/systemd/system/magnum-reconcile-periodic.service.tmp"
[Unit]
Description=Magnum Reconcile Periodic
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
ExecStart=/usr/local/bin/magnum-reconcile-launcher run-periodic
User=root
Group=root

# Do NOT auto-restart on failure. Periodic runs are drift correction; the timer
# fires them again on its own schedule. An immediate restart loop here would
# repeatedly re-acquire the reconcile flock for a rotation that is stuck (e.g.
# blocked at a CA-rotation barrier), starving Heat-triggered run-once invocations
# that wait on the same lock — a key reason a single timeout used to wedge every
# later operation.
Restart=no

# Same backstop as run-once so a hung periodic resume cannot squat the lock.
TimeoutStartSec=5100
TimeoutStopSec=120
KillMode=mixed
KillSignal=SIGTERM

# Limit CPU impact on cluster workloads during periodic drift checks.
Nice=15
CPUWeight=20
CPUQuota=50%

# Same cgroup memory backstop as the run-once unit (see note there): keep a
# runaway periodic Pulumi/Helm run from OOM-ing the node's control plane.
MemoryAccounting=yes
MemoryHigh=60%
EOF

cat <<EOF | $ssh_cmd "cat > /etc/systemd/system/magnum-reconcile.timer.tmp"
[Unit]
Description=Run Magnum Reconcile Periodically

[Timer]
OnActiveSec=5min
OnCalendar=*-*-* 00:00:00
# De-synchronize the fleet: without jitter every node reconciles at midnight
# sharp, and a change that triggers service restarts (cert heal, containerd
# config) restarts etcd/apiserver on all masters simultaneously — brief
# quorum/API loss. Per-node random delay keeps restarts staggered.
RandomizedDelaySec=45min
Unit=magnum-reconcile-periodic.service
Persistent=true

[Install]
WantedBy=timers.target
EOF

for unit in \
    /etc/systemd/system/magnum-reconcile.service \
    /etc/systemd/system/magnum-reconcile-periodic.service \
    /etc/systemd/system/magnum-reconcile.timer; do
    $ssh_cmd mv "${unit}.tmp" "${unit}"
    $ssh_cmd chown root:root "${unit}"
    $ssh_cmd chmod 644 "${unit}"
done

$ssh_cmd "if [ -d /run/systemd/system ]; then systemctl daemon-reload; fi"
