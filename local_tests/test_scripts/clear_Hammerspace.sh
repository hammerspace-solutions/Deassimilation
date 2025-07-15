#! /bin/bash
# Clear the /mnt/hs folder to reset the assimilation share

if mountpoint -q /mnt/hs; then
    echo "Clearing mount point /mnt/hs"
    rm -rf /mnt/hs/*
    ls -laR /mnt/hs
else
    echo ""
    echo "Failed - /mnt/hs is not mounted"
fi



