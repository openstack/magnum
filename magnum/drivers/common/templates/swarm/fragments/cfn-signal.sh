#!/bin/sh

. /etc/sysconfig/heat-params

echo "notifying heat"

STATUS="SUCCESS"
REASON="Setup complete"
DATA="OK"
UUID=`uuidgen`

data=$(echo '{"status": "'${STATUS}'", "reason": "'$REASON'", "data": "'${DATA}'", "id": "'$UUID'"}')

curl -k -i -X POST -H "Content-Type: application/json" -H "X-Auth-Token: $WAIT_HANDLE_TOKEN" \
    --data-binary "$data" \
    "$WAIT_HANDLE_ENDPOINT"
