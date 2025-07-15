#! /bin/bash
# Create 1 Million Files on NFS server between 10 and 30KB in size
# Should use ~25GB of drive space

if mountpoint -q /mnt/nfs-server; then
    echo "Creating 1 Million Files in /mnt/nfs-server"
    ./pTest.sh /mnt/nfs-server 1000000 20 30
else
    echo "Cannot create files, /mnt/nfs-server is not mounted"
fi
