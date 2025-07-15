#! /bin/bash
# generate a number of files with random sizes in a range 

if [ $# -lt 4 ]; then
    echo "Not enough arguments provided - please provide  FolderPath TotalFiles MinSize(KB) MaxSize(KB) for storage target"
    echo ""
    echo "Example: ./XXX.sh /Folder/Path 10000 100 500"
    echo ""
    exit 1
fi

if [ ! -d "$1" ]; then
    echo "Target folder specified in argument does not exist - correct and re-run"
    exit 1
fi

filepath=$1     # Path to Folder
totfiles=$2     # Total File Count
min=$3          # min file size (KB)
max=$4          # max file size (KB)
maxfiles=5000   # max number of files per directory
filecount=1
dircount=1
incr=$(($max - $min)) # Increment between min & max for random sizing

while [ $filecount -lt $totfiles ]; do
	mkdir -p "$1/TestData/Directory${dircount}"; 
	until [ $(($filecount % $maxfiles)) -eq 0 ]; do
		echo Creating ${filepath}/TestData/Directory${dircount}/file$( printf %03d "$filecount" ).bin
		dd if=/dev/urandom of=${filepath}/TestData/Directory${dircount}/file$( printf %03d "$filecount" ).bin bs=1K count=$(( $RANDOM%incr + $min )) 2>/dev/null
		if [ $filecount -eq $totfiles ]; then 
			exit 
		fi
		((++filecount))
	done
	if [ $filecount -eq $totfiles ]; then
		echo Creating ${filepath}/TestData/Directory${dircount}/file$( printf %03d "$filecount" ).bin
		dd if=/dev/urandom of=${filepath}/TestData/Directory${dircount}/file$( printf %03d "$filecount" ).bin bs=1K count=$(( $RANDOM%incr + $min )) 2>/dev/null
	else
		echo Creating ${filepath}/TestData/Directory${dircount}/file$( printf %03d "$filecount" ).bin
		dd if=/dev/urandom of=${filepath}/TestData/Directory${dircount}/file$( printf %03d "$filecount" ).bin bs=1K count=$(( $RANDOM%incr + $min )) 2>/dev/null
		((++dircount))
		((++filecount))
		if [ $filecount -eq $totfiles ]; then
			echo Creating ${filepath}/TestData/Directory${dircount}/file$( printf %03d "$filecount" ).bin
			dd if=/dev/urandom of=${filepath}/TestData/Directory${dircount}/file$( printf %03d "$filecount" ).bin bs=1K count=$(( $RANDOM%incr + $min )) 2>/dev/null
			exit
		fi			
	fi
done

