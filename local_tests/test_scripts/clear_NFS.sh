#! /bin/bash
# Clear the /mnt/nfs-server folder to reset the assimilation share

if mountpoint -q /mnt/nfs-server; then
    echo "Clearing mount point /mnt/nfs-server"
    rm -rf /mnt/nfs-server/*
    ls -laR /mnt/nfs-server
else
    echo ""
    echo "Failed - /mnt/nfs-server is not mounted"
fi



