#! /bin/bash
# Mount the Anvil server at 192.168.0.50 as NFSv4.2

if mountpoint -q /mnt/hs; then
	echo "ERROR - /mnt/hs is already mounted"
else
	mount -t nfs -o vers=4.2,port=20492 192.168.0.50:/assimilate /mnt/hs
	mount | grep "mnt/hs"
fi

