#!/bin/sh

. /etc/sysconfig/heat-params

echo "notifying heat"

STATUS="SUCCESS"
REASON="Setup complete"
DATA="OK"

data=$(echo '{"Status": "'${STATUS}'", "Reason": "'$REASON'", "Data": "'${DATA}'", "UniqueId": "00000"}')

curl -sf -X PUT -H 'Content-Type: application/json' \
    --data-binary "$data" \
    "$WAIT_HANDLE"
