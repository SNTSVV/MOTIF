#!/bin/bash

DISK_DEVICE="/dev/sda"
DISK_DEVICE_PART="/dev/sda1"

# Increase partition to Maximum
if [[ "$(parted -s -a opt ${DISK_DEVICE} "print free" | grep "Free Space" | wc -l)" == "2" ]]; then \
    parted -s -a opt ${DISK_DEVICE} "resizepart 1 100%"; \
    pvresize ${DISK_DEVICE_PART}; \
    lvextend -r -l +100%FREE /dev/mapper/vagrant--vg-root; \
fi

ROOT_FS_SIZE=`df -h / | sed -n 2p | awk '{print $2;}'`
echo "The root file system (/) has a size of $ROOT_FS_SIZE"

exit 0
