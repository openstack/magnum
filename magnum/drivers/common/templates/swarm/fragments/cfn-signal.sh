#!/bin/sh

. /etc/sysconfig/heat-params

echo "notifying heat"

STATUS="SUCCESS"
REASON="Setup complete"
DATA="OK"
UUID=`uuidgen`

data=$(echo '{"status": "'${STATUS}'", "reason": "'$REASON'", "data": "'${DATA}'", "id": "'$UUID'"}')

sh -c "${WAIT_CURL} --data-binary '${data}'"
