#!/bin/sh

. /etc/sysconfig/heat-params

echo "heat signal init"

if [ "$VERIFY_CA" == "True" ]; then
    VERIFY_CA=""
else
    VERIFY_CA="-k"
fi

function handle_error {
  local exit_code="$?"
  local line_number="$1"
  local error_message=$(echo "Exited with status $exit_code at line $line_number")

  escaped_error_message=\"${error_message//$'\n'/\\n}\"
  UUID=`uuidgen`
  echo ${escaped_error_message}
  
  $WAIT_CURL ${VERIFY_CA} --data-binary '{"status": "FAILURE", "reason": "Setup failed",  "id": "'$UUID'"}'
  exit $exit_code
}

trap 'handle_error $LINENO' ERR
