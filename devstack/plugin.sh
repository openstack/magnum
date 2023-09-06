# magnum.sh - Devstack extras script to install magnum

# Save trace setting
XTRACE=$(set +o | grep xtrace)
set -o xtrace

echo_summary "magnum's plugin.sh was called..."
source $DEST/magnum/devstack/lib/magnum
(set -o posix; set)

if is_service_enabled magnum-api magnum-cond; then
    if [[ "$1" == "stack" && "$2" == "install" ]]; then
        echo_summary "Installing magnum"
        install_magnum

        MAGNUM_GUEST_IMAGE_URL=${MAGNUM_GUEST_IMAGE_URL:-"https://builds.coreos.fedoraproject.org/prod/streams/stable/builds/35.20220116.3.0/x86_64/fedora-coreos-35.20220116.3.0-openstack.x86_64.qcow2.xz"}
        IMAGE_URLS+=",${MAGNUM_GUEST_IMAGE_URL}"

        LIBS_FROM_GIT="${LIBS_FROM_GIT},python-magnumclient"

        install_magnumclient
        cleanup_magnum
    elif [[ "$1" == "stack" && "$2" == "post-config" ]]; then
        echo_summary "Configuring magnum"
        configure_magnum

        # Hack a large timeout for now
        iniset /etc/keystone/keystone.conf token expiration 7200

        if is_service_enabled key; then
            create_magnum_accounts
        fi

        # Install kubectl and sonobuoy
        install_kubectl
        install_sonobuoy

    elif [[ "$1" == "stack" && "$2" == "extra" ]]; then
        # Initialize magnum
        init_magnum
        magnum_register_image
        magnum_configure_flavor

        # Start the magnum API and magnum taskmgr components
        echo_summary "Starting magnum"
        start_magnum

        configure_iptables_magnum
        configure_apache_magnum
    fi

    if [[ "$1" == "unstack" ]]; then
        stop_magnum
    fi

    if [[ "$1" == "clean" ]]; then
        cleanup_magnum
    fi
fi

# Restore xtrace
$XTRACE
