#!/bin/sh

. /etc/sysconfig/heat-params

if [ "$ENABLE_CINDER" == "False" ]; then
  # FIXME(yuanying): Use ephemeral disk for docker storage
  # Currently Ironic doesn't support cinder volumes,
  # so we must use preserved ephemeral disk instead of a cinder volume.
  device_path=$(readlink -f /dev/disk/by-label/ephemeral0)
else
  attempts=60
  while [ ${attempts} -gt 0 ]; do
      device_name=$(ls /dev/disk/by-id | grep ${DOCKER_VOLUME:0:20}$)
      if [ -n "${device_name}" ]; then
          break
      fi
      echo "waiting for disk device"
      sleep 0.5
      udevadm trigger
      let attempts--
  done

  if [ -z "${device_name}" ]; then
      echo "ERROR: disk device does not exist" >&2
      exit 1
  fi

  device_path=/dev/disk/by-id/${device_name}
fi

$configure_docker_storage_driver

if [ "$DOCKER_STORAGE_DRIVER" = "overlay" ]; then
    if [ $(echo -e "$(uname -r)\n3.18" | sort -V | head -1) \
         = $(uname -r) ]; then
        ERROR_MESSAGE="OverlayFS requires at least Linux kernel 3.18. Cluster node kernel version: $(uname -r)"
        echo "ERROR: ${ERROR_MESSAGE}" >&2
        sh -c "${WAIT_CURL} --data-binary '{\"status\": \"FAILURE\", \"reason\": \"${ERROR_MESSAGE}\"}'"
    else
        configure_overlay
    fi
else
    configure_devicemapper
fi
