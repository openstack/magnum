# magnum.sh - Devstack extras script to install magnum

if is_service_enabled m-api m-cond; then
    if [[ "$1" == "source" ]]; then
        # Initial source
        source $TOP_DIR/lib/magnum
    elif [[ "$1" == "stack" && "$2" == "install" ]]; then
        echo_summary "Installing magnum"
        install_magnum

        # add image to glance
        if [[ "$ENABLED_SERVICES" =~ 'm-api' ]]; then
            MANGUM_GUEST_IMAGE_URL=${MANGUM_GUEST_IMAGE_URL:-"https://fedorapeople.org/groups/heat/kolla/fedora-21-atomic-2.qcow2"}
            IMAGE_URLS+=",${MANGUM_GUEST_IMAGE_URL}"
        fi

        LIBS_FROM_GIT="${LIBS_FROM_GIT},python-magnumclient"

        install_magnumclient
        cleanup_magnum
    elif [[ "$1" == "stack" && "$2" == "post-config" ]]; then
        echo_summary "Configuring magnum"
        configure_magnum

        if is_service_enabled key; then
            create_magnum_accounts
        fi

    elif [[ "$1" == "stack" && "$2" == "extra" ]]; then
        # Initialize magnum
        init_magnum

        # Start the magnum API and magnum taskmgr components
        echo_summary "Starting magnum"
        start_magnum
    fi

    if [[ "$1" == "unstack" ]]; then
        stop_magnum
    fi

    if [[ "$1" == "clean" ]]; then
        cleanup_magnum
    fi
fi
