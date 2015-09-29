#!/bin/sh

. /etc/sysconfig/heat-params

echo "notifying heat"

STATUS="SUCCESS"
REASON="Setup complete"
DATA="OK"
FAILED_SERVICE=""

for service in $NODE_SERVICES; do
    echo "checking service status for $service"
    systemctl status $service
    if [[ $? -ne 0 ]]; then
        echo "$service is not active, the cluster is not valid"
        FAILED_SERVICE="$FAILED_SERVICE $service"
    fi
done

if [[ -n $FAILED_SERVICE ]]; then
    STATUS="FAILURE"
    REASON="Setup failed, $FAILED_SERVICE not start up correctly."
    DATA="Failed"
fi

data=$(echo '{"Status": "'${STATUS}'", "Reason": "'$REASON'", "Data": "'${DATA}'", "UniqueId": "00000"}')

curl -sf -X PUT -H 'Content-Type: application/json' \
    --data-binary "$data" \
    "$WAIT_HANDLE"
