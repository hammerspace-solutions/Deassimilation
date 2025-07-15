#!/usr/bin/env python
import os

print("Checking for Symbolic Links to Directories")
"""
for (dirpath, dirnames, filenames) in os.walk("/mnt/hs/"):
    print(dirpath)
    print(" ")
    for entry in os.scandir(dirpath):
#        print(entry) 
        if entry.is_dir() and entry.is_symlink():
            print("%s is a symlink to a directory" % entry.name)
#                deassimilate_dir(999, args, 999, entry.path, [])
print(" ")
print("Symbolic Link Scan Complete")

"""

def find_symbolic_links(start_path):
    symbolic_links = []

    for root, dirs, files in os.walk(start_path):
        for name in dirs + files:
            full_path = os.path.join(root, name)

#            if os.path.islink(full_path) and os.path.isdir(full_path):
#            if os.path.islink(full_path) and os.path.isdir(full_path):

            if os.path.isdir(full_path):
                symbolic_links.append(full_path)

    return symbolic_links

if __name__ == "__main__":
    # Replace '/path/to/start' with the directory you want to start scanning
    start_directory = '/mnt/hs'

    symbolic_links = find_symbolic_links(start_directory)

    if symbolic_links:
        print("Symbolic links found:")
        for link in symbolic_links:
            print(link)
    else:
        print("No symbolic links found.")

"""
 file_stat = os.lstat(share_full_fname)
valid_file_types = [ "REGULAR", "SYMLINK", "FIFO", "SOCK", "DEVBLK", "DEVCHR", "DIR" ]
def get_filetype(file_stat):
#   Convert the stat filetype to a string.  Valid options are in valid_file_types
#        module level list
#       valid_file_types = [ "REGULAR", "SYMLINK", "FIFO", "SOCK", "DEVBLK", "DEVCHR", "DIR" ]
    filetype = None
    file_stat_mode = file_stat.st_mode
    if stat.S_ISREG(file_stat_mode):
        filetype = "REGULAR"
    elif stat.S_ISLNK(file_stat_mode):
        filetype = "SYMLINK"
    elif stat.S_ISFIFO(file_stat_mode):
        filetype = "FIFO"
    elif stat.S_ISSOCK(file_stat_mode):
        filetype = "SOCK"
    elif stat.S_ISBLK(file_stat_mode):
        filetype = "DEVBLK"
    elif stat.S_ISCHR(file_stat_mode):
        filetype = "DEVCHR"
    elif stat.S_ISDIR(file_stat_mode):
        filetype = "DIR"
    return filetype



