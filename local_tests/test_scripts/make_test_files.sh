#!/bin/bash
# 
# Generate a default set of test files in the directory passed in first place

if [ -z "$1" ]
  then
    echo "Creating test files - Please provide target folder for files as an argument"
    exit 1
fi

if [ ! -d "$1" ]; then
    echo "Target folder specified in argument does not exist - correct and re-run"
    exit 1
fi


#### PUT CLICK-THROUGH TO ACKNOWLEDGE DELETING EVERYTHING HERE

RUNDIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
TEMPLATEFILE="$RUNDIR""/10000rows.txt"
FILECOUNT=1000

set -e -u

# Change to directory and delete everything in it
cd $1
sudo rm -rf *

# Create test directory structure
if [ ! -d "./dir00000000" ]; then
	mkdir ./dir00000000
	mkdir ./dir00000000/dir00000000
else
	echo "Target Folders exist"
fi

# Create test files in dirs
shuf -n $(shuf -i 100-1000 -n 1) $TEMPLATEFILE > ./dir00000000/file00000001
shuf -n $(shuf -i 100-1000 -n 1) $TEMPLATEFILE > ./dir00000000/dir00000000/file00000001

# Test symlink owner different from file owner is preserved
ln -s ./dir00000000/dir00000000/file00000001 01_test_asymlink_subdirfilenobody_test
sudo chown -h nobody:nobody  01_test_asymlink_subdirfilenobody_test

# Test pointing to a valid file
ln -s ./dir00000000/file00000001 02_test_asymlink_subdirfile_test

# Test pointing to a valid dir
ln -s ./dir00000000/ 03_test_asymlink_dir_test

# Test pointing to a valid subdir
ln -s ./dir00000000/dir00000000/ 04_test_asymlink_subdir_test

# Test pointing to a broken link inside a subdirectory
ln -s ./dir00000000/dir00000000/broken 05_test_asymlink_subsubdirbroken_test

# Test pointing to a broken link inside a directory
ln -s ./dir00000000/broken 06_test_asymlink_subdirbroken_test

# Test pointing to a broken link in the current directory
ln -s broken 07_test_asymlink_broken_test

# Test named pipe file
mkfifo 08_test.fifo

# Test socket file
python -c "import socket as s; sock = s.socket(s.AF_UNIX); sock.bind('09_test.sock')"

# ***Check /proc/devices for free numbers!****
# Test Block Device File 
sudo mknod 10_test.block b 250 0

# Test Character Device File
sudo mknod 11_test.char c 150 0

# Generate some sample files

mkdir ./data
i=1
while [[ $i -le $FILECOUNT ]]
do
    shuf -n $(shuf -i 100-1000 -n 1) $TEMPLATEFILE > ./data/${i}.text;
    ((i = i + 1))
done;

sudo chown -h -R nobody:nobody ./data

echo "This is some data" > ./testfile.txt

echo "this is someone else's file'" > ./otherowner.txt
sudo chown nobody:nobody ./otherowner.txt
sudo chmod 444 ./otherowner.txt

echo "Test Files Created"



