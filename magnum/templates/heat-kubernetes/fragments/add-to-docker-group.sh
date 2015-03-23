#!/bin/sh

# Under atomic, we need to make sure the 'dockerroot' group exists in
# /etc/group (because /lib/group cannot be modified by usermod).
echo "making 'dockerroot' group editable"
if ! grep -q dockerroot /etc/group; then
	grep dockerroot /lib/group >> /etc/group
fi

# make 'minion' user a member of the dockerroot group
# (so you can run docker commands as the 'minion' user)
echo "adding 'minion' user to 'dockerroot' group"
usermod -G dockerroot minion

