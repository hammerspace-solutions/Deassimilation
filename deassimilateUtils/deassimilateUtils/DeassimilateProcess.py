#!/usr/bin/env python3

# MIT License
#
# Copyright (c) 2025 Hammerspace, Inc
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
# -----------------------------------------------------------------------------
# DeassimilateProcess.py
#
# This routine will deassimilate a given directory (and only that directory)
# It is meant to be used within a DirectoryWalker process where that process
# will startup many DeassimilateProcess in order to get parallelism.
#

# Import Libraries

from __future__ import print_function

import argparse
import getpass
import json
import sys
import os
import shutil
import logging
import subprocess as sp
import requests as req
import stat
import socket
import urllib3

from pathlib import Path
from typing import Union, Callable, Any, List
from deassimilateUtils.Logger import Logger

# Define the name of the Program, Description, and Version.

progname = "DeassimilateProcess"
progdesc = "Deassimilate one single directory"
progvers = "1.0.0"

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Get filetype from stat
#
# valid types are "REGULAR", "SYMLINK", "FIFO", "SOCK', "DEVBLK", "DEVCHR", "DIR"

def get_filetype(file_stat):

    valid_file_types = [ "REGULAR", "SYMLINK", "FIFO", "SOCK", "DEVBLK", "DEVCHR", "DIR" ]
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

# Copy file attributes

def copy_file_attrs(src, dst, filetype, st, logger):

    if logger is not None:
        logger.debug(f"os.lchown({dst}, {st[stat.ST_UID]},{st[stat.ST_GID]}")
    os.lchown(dst, st[stat.ST_UID], st[stat.ST_GID])

    file_permissions_mode = stat.S_IMODE(st[stat.ST_MODE])
    if filetype in ("REGULAR", "DIR"):
        if logger is not None:
            logger.debug(f"os.chmod({dst}, {file_permissions_mode})")
        os.chmod(dst, file_permissions_mode)  # Use local version of lchmod
    else:
        # Note, See "Limitations" section of README.md
        if filetype in ("SYMLINK"):
            if logger is not None:
                logger.debug(f"os.chmod not supported symlink, " +
                             f"mode: {st[stat.ST_MODE]}, {dst}")
        else:
            if logger is not None:
                logger.error(f"os.chmod not support for file type" +
                             f" {filetype} with mode {st[stat.ST_MODE]} on file {dst}")

    if filetype in ("REGULAR", "DIR"):
        if logger is not None:
            logger.debug(f"os.utime({dst}, {st[stat.ST_ATIME]}" +
                         f", {st[stat.ST_MTIME]}")
        os.utime(dst, (st[stat.ST_ATIME], st[stat.ST_MTIME]))
    else:
        # Note, See "Limitations" section of README.md
        if logger is not None:
            logger.debug(f"Filetype {filetype} not supported for setting atime/mtime" +
                         f": {dst} {st[stat.ST_ATIME]}/{st[stat.ST_MTIME]}")

# Combine Paths

def combine_paths(base_path, sub_path):
    stripped_sub = sub_path.lstrip("/")
    combined = Path(base_path) / Path(stripped_sub)
    combined_with_slash = f"{combined}/" \
        if not str(combined).endswith("/") else f"{combined}/"

    return combined_with_slash

# Rename the file if a ? exists in the pathname
# This is called by get_inode_info below
    
def temp_rename(path: str, func: Callable[[str], Any]) -> Any:

    path_obj = Path(path)
    if "?" not in path_obj.name:
        # No question mark, just execute the function
        return func(str(path_obj))
    
    # Generate temporary name by replacing ? with a safe string
    temp_name = path_obj.name.replace("?", "_TEMPQMARK_")
    temp_path = path_obj.with_name(temp_name)
    
    # Rename original to temporary
    shutil.move(str(path_obj), str(temp_path))
    
    try:
        # Execute the function
        result = func(str(temp_path))
    except Exception as e:
        # Always attempt to rename back, even if func() raised an exception
        shutil.move(str(temp_path), str(path_obj))
        raise e
    
    # Rename back to original
    shutil.move(str(temp_path), str(path_obj))
    
    return result

# Get the inode info from the shadow filesystem. The problem is with a pathname
# that already has a "?" in it. This is the trigger for a shadow filesystem call
# and can cause that call to fail because it is a valid character in the pathname.
# So, we might have to rename the file to remove the "?" so that we can make
# the call... Clearly, after the shadow filesystem call, we have to rename the
# filename back
    
def get_inode_info(path: str) -> str:
    def _get_info(path: str):
        # This is where you'd call your specialized filesystem operation
        # For example: path + "?.attributes=inode_info"
        # Since we're in the temp renamed state, the ? won't conflict
        attr_path = path + "?.attribute=inode_info"
        with open(attr_path, 'r') as fp:
            inode_info = json.load(fp)
            return inode_info
    
    return temp_rename(path, _get_info)

# Deassimilate directory

def deassimilate_dir(dirpath: Path,
                     filenames: List,
                     logger = None,
                     sharemnt: str=None,
                     share_root: str=None,
                     volmnt: str=None,
                     volid: int=None):

    # Debugging only

    if logger is not None:
        logger.debug(f"deassimilate: {dirpath}, # files: {len(filenames)}")
        logger.debug(f"   sharemnt={sharemnt}, share_root={share_root}")
        logger.debug(f"   volmnt={volmnt}, volid={volid}")

    # For counting extensions

    extension_counts = {}
    total_size = 0
    
    if len(sharemnt) != len(str(dirpath)):
        temp_path = combine_paths(volmnt,
                                  share_root)
        vol_path = combine_paths(temp_path,
                                 str(dirpath)[len(sharemnt):])
    else:
        vol_path = combine_paths(volmnt,
                                 share_root)

    # Find out if it is a symlink for a directory

    dir_stat = os.lstat(dirpath)
    dir_type = get_filetype(dir_stat)
    if dir_type == "SYMLINK":
        if logger is not None:
            logger.info(f"Directory symlink detected: {dirpath}")

        # Strip the ending "/" from the vol_path or the symlink won't work

        if vol_path.endswith("/"):
            vol_path = Path(str(vol_path).rstrip("/"))

        # Build a symlink for this directory

        symlinkdest = os.readlink(dirpath)
        if logger is not None:
            logger.debug(f"os.readlink({dirpath}) -> {symlinkdest}")

        # Build the symlink to the volume and not the share
        
        try:
            os.symlink(symlinkdest, vol_path)
        except OSError as e:
            if e.errno == 17:
                # Symlink exists already
                if logger is not None:
                    logger.warning(f"Symlink {symlinkdest} already exists!")
            else:
                if logger is not None:
                    logger.error(f"Symlink {symlinkdest} error: {e}")
                    raise e

        # Copy the attributes

        copy_file_attrs(dirpath,
                        vol_path,
                        dir_type,
                        dir_stat,
                        logger)
        
        if logger is not None:
            logger.info(f"Symlink created: {symlinkdest} -> {dirpath}")

    # Just a normal directory... Process it and any files
    
    else:
        if logger is not None:
            logger.debug(f"From {dirpath} to {vol_path}")

        # Setup target directory
        # A subdirectory may be generated before its parents. Create all of them
        # and have the permissions fixed up int he follow on thread.
        
        if not os.path.isdir(vol_path):
            if logger is not None:
                logger.debug(f"os.makedirs({vol_path})")

            # This could fail if somebody is fast enough to make the directory
            # before we can
            
            try:
                os.makedirs(vol_path, exist_ok=True)
            except OSError as e:
                if logger is not None:
                    logger.error(f"os.makedirs error: {e}")

        elif os.path.isdir(vol_path):
            if logger is not None:
                logger.debug(f"Directory {vol_path} already exists")

        # Get the stat of the directory and copy the attributes to the new directory

        copy_file_attrs(str(dirpath),
                        vol_path,
                        "DIR",
                        dir_stat,
                        logger)

        # Walk through every file and create a hard link for it.

        if len(filenames) > 0:
            for fn in filenames:

                share_full_fname = os.path.join(dirpath, fn)
                vol_full_fname = os.path.join(vol_path, fn)

                if logger is not None:
                    logger.debug(f"vol_path: {vol_path}, filename: {fn}")
                    logger.debug(f"share_full_fname: {share_full_fname}")
                    logger.debug(f"vol_full_fname: {vol_full_fname}")
                    
                file_stat = os.lstat(share_full_fname)

                # Get the file name suffix... We are only doing this for statistical
                # purposes

                ext = Path(share_full_fname).suffix.lower()
                extension_counts[ext] = extension_counts.get(ext, 0) + 1

                # Get the total size of the data processed
        
                total_size += file_stat[stat.ST_SIZE]

                # Get the filetype so that we can process it correctly
        
                filetype = get_filetype(file_stat)

                # If the file is just a "regular" file
            
                if filetype == "REGULAR":
                    if logger is not None:
                        logger.debug(f"os.lstat({share_full_fname})" +
                                     f" regular file with size {file_stat[stat.ST_SIZE]}")

                    # Get the inode info from the shadow filesystem on the Hammerspace
                    # You can always tell this is happening when you see a "?" appended
                    # to a pathname..
                    #
                    # Here is where it gets dangerous...
                    #
                    # What if a customer pathname contains a "?" already? This means
                    # that the shadow filesystem lookup will fail.
                    #
                    # So we will make sure this doesn't happen by renaming the path
                    # to have NO "?" in the filename, getting the shadow filesystem
                    # info and then renaming the file back

                    inode_info = get_inode_info(share_full_fname)

                    # If there is no instance of this file in the comb structure,
                    # then print an error and move on
                
                    if 'instance' not in inode_info or len(inode_info['instance']) < 1:
                        if logger is not None:
                            logger.error(f"error {share_full_fname}" +
                                         f" does not have an instance inode_info section" +
                                         f". Skipping...")
                        continue

                    # Find the instance in the comb structure
                
                    found_instance = False
                    path_instance = ""
                
                    for instance in range(len(inode_info['instance'])):
                        if inode_info['instance'][instance]['obs'] == volid:
                            path_instance = os.path.join(volmnt,
                                                         inode_info['instance'][instance]['path'][1:])
                            found_instance = True
                            break
                        
                    # If not in the comb structure, move on
                
                    if not found_instance:
                        if logger is not None:
                            logger.error(f"error {share_full_fname}" +
                                         f" does not have an instance on needed volume id")
                        continue

                    # note there is something up with % substitution here with UTF-8
                    # characters. Use .format

                    if logger is not None:
                        logger.debug(f"os.link({path_instance}" +
                                     f", {vol_full_fname}")

                    # Create a hard link

                    try:
                        os.link(path_instance, vol_full_fname)
                    except OSError as e:
                        if e.errno == 17:
                            # File exists
                            if logger is not None:
                                logger.error(f"File already exists" +
                                             f", skipping, os.link({path_instance}" +
                                             f", {vol_full_fname}")
                        else:
                            if logger is not None:
                                logger.info(f"os.link error on file share {share_full_fname}" +
                                            f", {vol_full_fname} volume" +
                                            f": {path_instance} instance: {e}")
                                raise e

                # If the file is a symbolic link
            
                elif filetype == "SYMLINK":
                    if logger is not None:
                        logger.debug(f"os.lstat({file_stat[stat.ST_SIZE]}")
                    symlinkdest = os.readlink(share_full_fname)
                    if logger is not None:
                        logger.debug(f"os.readlink({share_full_fname}" +
                                     f") -> {symlinkdest}")

                    # Create a symlink
                
                    try:
                        os.symlink(symlinkdest, vol_full_fname)
                    except OSError as e:
                        if e.errno == 17:
                            # File exists
                            if logger is not None:
                                logger.warning(f"Symlink already exists, " +
                                               f"skipping, os.symlink({symlinkdest}" +
                                               f", {vol_full_fname}) failed")
                        else:
                            if logger is not None:
                                logger.error(f"os.symlink() error on file " +
                                             f"share:{share_full_fname}, " +
                                             f"volume:{vol_full_fname}: {e}")
                                raise e

                    if logger is not None:
                        logger.debug(f"os.symlink({symlinkdest}" +
                                     f", {vol_full_fname}")

                    # Copy the file attributes for the newly hard linked file
            
                    copy_file_attrs(share_full_fname,
                                    vol_full_fname,
                                    filetype,
                                    file_stat,
                                    logger)

    return {
        "directory": str(dirpath),
        "total_files": len(filenames),
        "extension_counts": extension_counts,
        "total_size_bytes": total_size
    }
