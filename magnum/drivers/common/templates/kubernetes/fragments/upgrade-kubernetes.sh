. /etc/sysconfig/heat-params
set -x

ssh_cmd="ssh -F /srv/magnum/.ssh/config root@localhost"
KUBECONFIG="/etc/kubernetes/kubelet-config.yaml"
if [ "$(echo $USE_PODMAN | tr '[:upper:]' '[:lower:]')" == "true" ]; then
    kubecontrol="/srv/magnum/bin/kubectl --kubeconfig $KUBECONFIG"
else
    kubecontrol="/var/lib/containers/atomic/heat-container-agent.0/rootfs/usr/bin/kubectl --kubeconfig $KUBECONFIG"
fi
new_kube_tag="$kube_tag_input"
new_kube_image_digest="$kube_image_digest_input"
new_ostree_remote="$ostree_remote_input"
new_ostree_commit="$ostree_commit_input"

function drain {
    # If there is only one master and this is the master node, skip the drain, just cordon it
    # If there is only one worker and this is the worker node, skip the drain, just cordon it
    all_masters=$(${ssh_cmd} ${kubecontrol} get nodes --selector=node-role.kubernetes.io/control-plane= -o name)
    all_workers=$(${ssh_cmd} ${kubecontrol} get nodes --selector=node-role.kubernetes.io/control-plane!= -o name)
    if [ "node/${INSTANCE_NAME}" != "${all_masters}" ] && [ "node/${INSTANCE_NAME}" != "${all_workers}" ]; then
        ${ssh_cmd} ${kubecontrol} drain ${INSTANCE_NAME} --ignore-daemonsets --delete-local-data --force
    else
        ${ssh_cmd} ${kubecontrol} cordon ${INSTANCE_NAME}
    fi
}

if [ "${new_kube_tag}" != "${KUBE_TAG}" ]; then

    drain

    if [ "$(echo $USE_PODMAN | tr '[:upper:]' '[:lower:]')" == "true" ]; then
        SERVICE_LIST=$($ssh_cmd podman ps -f name=kube --format {{.Names}})

        for service in ${SERVICE_LIST}; do
            ${ssh_cmd} systemctl stop ${service}
            ${ssh_cmd} podman rm ${service}
        done

        ${ssh_cmd} podman rmi ${CONTAINER_INFRA_PREFIX:-${HYPERKUBE_PREFIX}}hyperkube:${KUBE_TAG}
        echo "KUBE_TAG=$new_kube_tag" >> /etc/sysconfig/heat-params

        for service in ${SERVICE_LIST}; do
            ${ssh_cmd} systemctl start ${service}
        done

        i=0
        until [ "`${ssh_cmd} podman image exists ${CONTAINER_INFRA_PREFIX:-${HYPERKUBE_PREFIX}}hyperkube:${new_kube_tag} && echo $?`" = 0 ]
        do
            i=$((i+1))
            [ $i -lt 30 ] || break;
            echo "Pulling image: hyperkube:${new_kube_tag}"
            sleep 5s
        done

        KUBE_DIGEST=$($ssh_cmd podman image inspect ${CONTAINER_INFRA_PREFIX:-${HYPERKUBE_PREFIX}}hyperkube:${new_kube_tag} --format "{{.Digest}}")
        if [ -n "${new_kube_image_digest}"  ] && [ "${new_kube_image_digest}" != "${KUBE_DIGEST}" ]; then
            printf "The sha256 ${KUBE_DIGEST} of current hyperkube image cannot match the given one: ${new_kube_image_digest}."
            exit 1
        fi

        i=0
        until ${ssh_cmd} ${kubecontrol} uncordon ${INSTANCE_NAME}
        do
            i=$((i+1))
            [ $i -lt 30 ] || break;
            echo "Trying to uncordon node..."
            sleep 5s
        done
    else
        declare -A service_image_mapping
        service_image_mapping=( ["kubelet"]="kubernetes-kubelet" ["kube-controller-manager"]="kubernetes-controller-manager" ["kube-scheduler"]="kubernetes-scheduler" ["kube-proxy"]="kubernetes-proxy" ["kube-apiserver"]="kubernetes-apiserver" )

        SERVICE_LIST=$($ssh_cmd atomic containers list -f container=kube -q --no-trunc)

        for service in ${SERVICE_LIST}; do
            ${ssh_cmd} systemctl stop ${service}
        done

        for service in ${SERVICE_LIST}; do
            ${ssh_cmd} atomic pull --storage ostree "${CONTAINER_INFRA_PREFIX:-docker.io/openstackmagnum/}${service_image_mapping[${service}]}:${new_kube_tag}"
        done

        for service in ${SERVICE_LIST}; do
            ${ssh_cmd} atomic containers update --rebase ${CONTAINER_INFRA_PREFIX:-docker.io/openstackmagnum/}${service_image_mapping[${service}]}:${new_kube_tag} ${service}
        done

        for service in ${SERVICE_LIST}; do
            systemctl restart ${service}
        done

        ${ssh_cmd} ${kubecontrol} uncordon ${INSTANCE_NAME}

        for service in ${SERVICE_LIST}; do
            ${ssh_cmd} atomic --assumeyes images "delete ${CONTAINER_INFRA_PREFIX:-docker.io/openstackmagnum/}${service_image_mapping[${service}]}:${KUBE_TAG}"
        done

        ${ssh_cmd} atomic images prune
    fi
fi

function setup_uncordon {
    # Create a service to uncordon the node itself after reboot
    if [ ! -f /etc/systemd/system/uncordon.service ]; then
        $ssh_cmd cat > /etc/systemd/system/uncordon.service << EOF
[Unit]
Description=magnum-uncordon
After=network.target kubelet.service

[Service]
Restart=always
RemainAfterExit=yes
RestartSec=10
ExecStart=${kubecontrol} uncordon ${INSTANCE_NAME}

[Install]
WantedBy=multi-user.target
EOF
        ${ssh_cmd} systemctl enable uncordon.service
    fi
}

# NOTE(flwang): Record starts with "*" means the current one
current_ostree_commit=`${ssh_cmd} rpm-ostree status | grep -A 3 "* ostree://" | grep Commit | awk '{print $2}'`
current_ostree_remote=`${ssh_cmd} rpm-ostree status | awk '/* ostree/{print $0}' | awk '{match($0,"* ostree://([^ ]+)",a)}END{print a[1]}'`
remote_list=`${ssh_cmd} ostree remote list`

# NOTE(flwang): This part is only applicable for fedora atomic
if [[ $current_ostree_remote == *"fedora-atomic"* ]]; then
    # Fedora Atomic 29 will be the last release before migrating to Fedora CoreOS, so we're OK to add 28 and 29 remotes directly
    if [[ ! " ${remote_list[@]} " =~ "fedora-atomic-28" ]]; then
        ${ssh_cmd} ostree remote add --set=gpgkeypath=/etc/pki/rpm-gpg/RPM-GPG-KEY-fedora-28-primary --contenturl=mirrorlist=https://ostree.fedoraproject.org/mirrorlist fedora-atomic-28 https://kojipkgs.fedoraproject.org/atomic/repo/
    fi
    if [[ ! " ${remote_list[@]} " =~ "fedora-atomic-29" ]]; then
        ${ssh_cmd} ostree remote add --set=gpgkeypath=/etc/pki/rpm-gpg/RPM-GPG-KEY-fedora-29-primary --contenturl=mirrorlist=https://ostree.fedoraproject.org/mirrorlist fedora-atomic-29 https://kojipkgs.fedoraproject.org/atomic/repo/
    fi
    # The uri of existing Fedora Atomic 27 remote is not accessible now, so replace it with correct uri
    if [[ " ${remote_list[@]} " =~ "fedora-atomic" ]]; then
        sed -i '
            /^url=/ s|=.*|=https://kojipkgs.fedoraproject.org/atomic/repo/|
        ' /etc/ostree/remotes.d/fedora-atomic.conf
    fi
fi

# NOTE(flwang): 1. Either deploy or rebase for only one upgrade
#               2. Using rpm-ostree command instead of atomic command to keep the possibility of supporting fedora coreos 30
if [ "$new_ostree_commit" != "" ] && [ "$current_ostree_commit" != "$new_ostree_commit" ]; then
    drain
    setup_uncordon
    ${ssh_cmd} rpm-ostree deploy $new_ostree_commit
    shutdown --reboot --no-wall -t 1
elif [ "$new_ostree_remote" != "" ] && [ "$current_ostree_remote" != "$new_ostree_remote" ]; then
    drain
    setup_uncordon
    ${ssh_cmd} rpm-ostree rebase $new_ostree_remote
    shutdown --reboot --no-wall -t 1
fi
