#!/bin/bash
set -x

for i in $(seq 24)
do
	echo "---------------------------------------------"
	cat /var/log/openvpn.log
	echo "---------------------------------------------"
	echo

	#if grep -q "Initialization Sequence Completed" /var/log/openvpn.log; then
	if grep -q "/sbin/ip addr add dev" /var/log/openvpn.log; then
		sleep 5
		exit 0
	fi
	sleep 5
done

echo "ERROR: VPN doesn't seem to have initialized"
exit 1

