#! /bin/bash
# Mount the NFS server at 192.168.0.60 as NFS

if mountpoint -q /mnt/nfs-server; then
	echo "ERROR - /mnt/nfs-server is already mounted"
else
	mount 192.168.0.60:/srv/nfs-server /mnt/nfs-server
	mount | grep "mnt/nfs-server"
fi


