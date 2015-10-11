#!/bin/sh

. /etc/sysconfig/heat-params

if [ "$RHN_REGISTER" = true -o "$RHN_REGISTER" = True ]; then
	echo "registering with RHN"
	subscription-manager register --auto-attach \
		--username="$RHN_USERNAME" \
		--password="$RHN_PASSWORD"
fi

