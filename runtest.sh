#!/bin/bash
# 
# 

if mountpoint -q /mnt/nfs-server; then
    echo "Running Deassimilation Test"
	# Delete old folder from previous tests
	rm -rf /mnt/nfs-server/assimilate
	
	# Delete old deassimilation log
	if [ -f ./deassimilate.log ] ; then
		rm ./deassimilate.log
	fi

	# Run deassimilation script with selective parameters
	./deassimilate.py\
	 --ds 192.168.0.50\
	 --authfile auth.txt\
	 --numjobs 20
#	 --volid 32\
#	 --shareid 6\
#	 --mntdir /mnt/nfs-server/
	# --local-files-path "/mnt/nfs"
	sleep 5
	clear;ls -la /mnt/hs; ls -la /mnt/nfs-server/assimilate/
else
    echo "Cannot delete old deassim folder, /mnt/nfs-server is not mounted"
    exit 1
fi


