#!/bin/sh

. /etc/sysconfig/heat-params

echo "notifying success to heat"

if [ "$VERIFY_CA" == "True" ]; then
    VERIFY_CA=""
else
    VERIFY_CA="-k"
fi

UUID=`uuidgen`

$WAIT_CURL ${VERIFY_CA} --data-binary '{"status": "SUCCESS", "reason": "Setup complete", "data": "OK", "id": "'$UUID'"}'
