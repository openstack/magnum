# magnum.sh - Devstack extras script to install magnum

# Save trace setting
XTRACE=$(set +o | grep xtrace)
set -o xtrace

echo_summary "magnum's plugin.sh was called..."
source $DEST/magnum/devstack/lib/magnum
(set -o posix; set)

if is_service_enabled m-api m-cond; then
    if [[ "$1" == "stack" && "$2" == "pre-install" ]]; then
        echo_summary "Before Installing magnum"
        mkdir -p $SCREEN_LOGDIR
        if [[ -z `grep 'python-kubernetes' ${REQUIREMENTS_DIR}/global-requirements.txt` ]]; then
            echo "python-kubernetes>=0.2" >> ${REQUIREMENTS_DIR}/global-requirements.txt
        fi
        if [[ -z `grep 'docker-py' ${REQUIREMENTS_DIR}/global-requirements.txt` ]]; then
            sed -i 's/requests>=.*/requests>=2.5.2/g' ${REQUIREMENTS_DIR}/global-requirements.txt
            echo "docker-py>=1.1.0" >> ${REQUIREMENTS_DIR}/global-requirements.txt
        fi
    elif [[ "$1" == "stack" && "$2" == "install" ]]; then
        echo_summary "Installing magnum"
        install_magnum

        # add image to glance
        if [[ "$ENABLED_SERVICES" =~ 'm-api' ]]; then
            MANGUM_GUEST_IMAGE_URL=${MANGUM_GUEST_IMAGE_URL:-"https://fedorapeople.org/groups/magnum/fedora-21-atomic-2.qcow2"}
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

# Restore xtrace
$XTRACE
