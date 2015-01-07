#!/bin/sh

# Under atomic, we need to make sure the 'docker' group exists in 
# /etc/group (because /lib/group cannot be modified by usermod).
echo "making 'docker' group editable"
if ! grep -q docker /etc/group; then
	grep docker /lib/group >> /etc/group
fi

# make 'minion' user a member of the docker group
# (so you can run docker commands as the 'minion' user)
echo "adding 'minion' user to 'docker' group"
usermod -G docker minion

