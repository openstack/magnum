# magnum.sh - Devstack extras script to install magnum

# Save trace setting
XTRACE=$(set +o | grep xtrace)
set -o xtrace

echo_summary "magnum's plugin.sh was called..."
source $DEST/magnum/devstack/lib/magnum
(set -o posix; set)

if is_service_enabled m-api m-cond; then
    if [[ "$1" == "stack" && "$2" == "install" ]]; then
        echo_summary "Installing magnum"
        install_magnum

        # add image to glance
        if [[ "$ENABLED_SERVICES" =~ 'm-api' ]]; then
            # TODO Add a "latest" link to fedora release process
            ATOMIC_IMAGE_NAME=$( \
                wget --spider --level 1 \
                     --recursive --accept-regex=".*qcow2" \
                     "https://alt.fedoraproject.org/pub/alt/atomic/stable/Cloud-Images/x86_64/Images/" 2>&1 | \
                grep qcow2 | \
                sed 's/.*Cloud-Images\/x86_64\/Images\///' | \
                head -n 1)
            echo "Atomic Image: $ATOMIC_IMAGE_NAME"
            MAGNUM_GUEST_IMAGE_URL=${MAGNUM_GUEST_IMAGE_URL:-"https://download.fedoraproject.org/pub/alt/atomic/stable/Cloud-Images/x86_64/Images/$ATOMIC_IMAGE_NAME"}
            IMAGE_URLS+=",${MAGNUM_GUEST_IMAGE_URL}"
        fi

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

    elif [[ "$1" == "stack" && "$2" == "extra" ]]; then
        # Initialize magnum
        init_magnum
        magnum_register_image

        # Start the magnum API and magnum taskmgr components
        echo_summary "Starting magnum"
        start_magnum

        configure_iptables
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
