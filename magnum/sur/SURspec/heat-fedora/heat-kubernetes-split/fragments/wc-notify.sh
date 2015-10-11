#!/bin/bash -v

. /etc/sysconfig/heat-params

echo "Notifying heat"

cat <<EOF | curl -sf -X PUT -H 'Content-Type: application/json' \
	--data-binary @- "$WAIT_HANDLE" 
{
	"Status": "SUCCESS",
}
EOF

