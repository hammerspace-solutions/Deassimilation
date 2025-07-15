#!/usr/bin/env python

import os
import filecmp
import difflib

def compare_folders(dir1, dir2):
    print("Comparing %s and %s" % (dir1, dir2))
    dcmp = filecmp.dircmp(dir1, dir2)
    
    # Compare files
    for file in dcmp.diff_files:
        file1 = os.path.join(dir1, file)
        file2 = os.path.join(dir2, file)
        print(f"File {file} differs:")
        compare_files(file1, file2)

    # Compare directories recursively
    for sub_dir in dcmp.subdirs:
        compare_folders(os.path.join(dir1, sub_dir), os.path.join(dir2, sub_dir))

def compare_files(file1, file2):
    with open(file1, 'r') as f1, open(file2, 'r') as f2:
        diff = difflib.unified_diff(f1.readlines(), f2.readlines(), lineterm='', fromfile=file1, tofile=file2)
        for line in diff:
            print(line)

if __name__ == "__main__":
    folder1 = "/mnt/hs/"
    folder2 = "/mnt/nfs-server/assimilate/"
    print("Checking folders")
    compare_folders(folder1, folder2)
