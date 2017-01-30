#!/bin/sh

. /etc/sysconfig/heat-params

echo "notifying heat"

STATUS="SUCCESS"
REASON="Setup complete"
DATA="OK"
UUID=`uuidgen`

data=$(echo '{"Status": "'${STATUS}'", "Reason": "'$REASON'", "Data": "'${DATA}'", "Id": "'$UUID'"}')

curl -k -i -X POST -H "Content-Type: application/json" -H "X-Auth-Token: $WAIT_HANDLE_TOKEN" \
    --data-binary "'$data'" \
    "$WAIT_HANDLE_ENDPOINT"
