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
# deassimilate.py
#
# Recreate the directory structure of a Hammerspace share on to a particular
# volume using hardlinks.
#
# AKA uninstall
#
# Requires that mobility has been used to move all files in the given share on
# to the target volume otherwise uninstall will fail.  See README.md for full details
#
# REST docs are at https://<anvil>:8443/mgmt/swagger/index.html
#

# Import Libraries

from __future__ import print_function

import argparse
import getpass
import sys
import os
import subprocess as sp
import requests as req
import stat
import socket
import ipaddress
import urllib3
import humanize

from pathlib import Path
from typing import Union, Callable, Any
from deassimilateUtils.Logger import Logger
from deassimilateUtils.DeassimilateProcess import (deassimilate_dir,
                                                   combine_paths)
from deassimilateUtils.DirectoryWalker import (DirectoryWalker,
                                               CustomResultProcessor,
                                               DefaultResultProcessor)

# Define the name of the Program, Description, and Version.

progname = "deassimilate"
progdesc = "Deassimilate data back into native filesystems"
progvers = "1.0.0"

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Class to get the password from a command line

class Password:
    DEFAULT = None

    def __init__(self, value):
        if value is None:
            value = getpass.getpass('Password: ')
        self.value = value

    def __str__(self):
        return self.value
    

# Deassimilate Class
#
# Here is where 100% of the work is done.

class deassimilate(object):

    def __init__(self, args, logger):

        self.args = args
        self.logger = logger
        self.ds_rest = f"https://{args.host}:8443/mgmt/v1.2/rest/"
        self.args.sharemnt = os.path.join(args.mntdir, "share")
        self.args.volmnt = os.path.join(args.mntdir, "vol")
        self.anvil = None
        self.volume_details = []
        self.share_details = []
        self.selected_volume = {}
        self.selected_share = {}
        
    def setup(self):

        # Start by verifying that the machine is local

        if not self.is_local(self.args.host):
            self.logger.error("This code cannot run on a Hammerspace node")
            sys.exit(1)

        # Login to the Anvil so that we can find the volumes and shares
        # that they might want to work on.

        try:
            self.login(self.args.username,
                       self.args.password)
        except (Exception,) as excpt:
            self.logger.error(f"Unable to login to Anvil. Error is {excpt}")
            sys.exit(1)

        self.logger.debug("Logged into Anvil")
        
    def run(self):

        # If they want to list-volumes, then go and get them

        self.get_share_volume()

        if self.args.list_volumes:
            self.logger.info("Volumes:")
            for volume in self.volume_details:
                self.logger.info(f"  {volume['id']}: {volume['name']}" +
                                 f" {volume['ip']}:{volume['path']}")
            self.logger.info("Shares:")
            for share in self.share_details:
                self.logger.info(f"  {share['id']}: {share['name']}" +
                                 f" {share['path']} {share['num_files']} files")
            sys.exit(0)

        else:

            # Make sure that we have the volid and shareid that they want to work on

            if self.args.volid is None or self.args.shareid is None:
                self.logger.error("Must specify a volume and share")
                sys.exit(1)

            # Pick the selected volume based upon volid

            for volume in self.volume_details:
                if volume['id'] == self.args.volid:
                    self.selected_volume = volume
                    break

            # If we don't have a selected_volume, then print out an error message and exit

            if self.selected_volume == {}:
                self.logger.error(f"Volume id: {self.args.volid} not found")
                sys.exit(1)

            # Pick the selected share based upon shareid

            for share in self.share_details:
                if share['id'] == self.args.shareid:
                    self.selected_share = share
                    self.args.share_root_path = share['path']
                    break

            # If we don't have a selected_share, then print out an error message and exit

            if self.selected_share == {}:
                self.logger.error(f"Share id: {self.args.shareid} not found")
                sys.exit(1)

            # Mount the selected share and volume

            self.mount_share_volume()

            # Walk through the directories and start the deassimilation process
            # There are actually two ways to call this... This first one is
            # when we don't want to use multiprocessing

            if self.args.singleprocess:
                for (dirpath, dirnames, filenames) in os.walk(self.args.sharemnt):
                    deassimilate_dir(dirpath,
                                     filenames,
                                     sharemnt=self.args.sharemnt,
                                     share_root=self.args.share_root_path,
                                     volmnt=self.args.volmnt,
                                     volid=self.args.volid,
                                     logger=self.logger)

            # Here is where we handle the same function, but with multiprocessing

            else:

                # Do they want directory statistics or not?

                if self.args.statistics:
                    result_processor = CustomResultProcessor(self.logger)
                else:
                    result_processor = DefaultResultProcessor(self.logger)
                
                walker = DirectoryWalker(
                    processor_func=deassimilate_dir,
                    max_processes=self.args.numjobs,
                    name=progname,
                    description=progdesc,
                    version=progvers,
                    logger=self.logger,
                    result_processor=result_processor,
                    sharemnt=self.args.sharemnt,
                    share_root=self.args.share_root_path,
                    volmnt=self.args.volmnt,
                    volid=self.args.volid)

                # Start the parallel processing
                
                walker.walk_directories(self.args.sharemnt)
                
            # Walk through the directories again to check for Symlink
            # to directories
            
            self.logger.info("Checking for Symbolic Links to Directories")
            for (dirpath, dirnames, filenames) in os.walk(self.args.sharemnt):
                for entry in os.scandir(dirpath):
                    if entry.is_dir() and entry.is_symlink():
                        deassimilate_dir(entry.path, [],
                                         sharemnt=self.args.sharemnt,
                                         share_root=self.args.share_root_path,
                                         volmnt=self.args.volmnt,
                                         volid=self.args.volid,
                                         logger=self.logger)
            self.logger.info("Symbolic Link Scan Complete")

            # Run rsync to verify that everything has moved

#            dest_path = combine_paths(self.args.volmnt, self.args.share_root_path)
#            self.rsync_check(self.args.sharemnt, dest_path)
                             
            # Print out final statistics if they want them

            if (self.args.statistics or self.args.totals) and not self.args.singleprocess:
                self.logger.info("\nProcessing Summary:")
                self.logger.info(f"Directories: {result_processor.total_directories}")
                self.logger.info(f"Files: {result_processor.total_files}")
                self.logger.info(f"Total Size: {humanize.naturalsize(result_processor.total_size)}")
                
    # This routine tears down all of the structures created during class operations.
    # We don't really care since python garbage collection is so good.
    #
    # But, we do want to know the count of the number of directories, files,
    # and symlinks were handled.
    
    def teardown(self):

#        self.umount_share_volume(create_dirs=False)
        pass

    # Perform a rsync to verify that the data is all deassimilated

    def rsync_check(self, source_path=None, dest_path=None):

        self.logger.info("Running rsync dry run to validate metadata")

        cmd = f"rsync --dry-run -iarAXUH --delete {source_path} {dest_path}"
        grep_cmd = "grep -v ^.d..t"

        # Open the pipes to execute both rsync and grep

        rsync_process = sp.Popen(cmd.split(),
                                 stdout=sp.PIPE,
                                 text=True)
        grep_process = sp.Popen(grep_cmd.split(),
                                stdin=rsync_process.stdout,
                                stdout=sp.PIPE,
                                text=True)
        output, error = grep_process.communicate()

        # Rsync output

        self.logger.info(f"{output}")
        self.logger.info("Rsync check complete")
        
    # Get filetype from stat
    #
    # valid types are "REGULAR", "SYMLINK", "FIFO", "SOCK', "DEVBLK", "DEVCHR", "DIR"

    def get_filetype(self, file_stat):

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

    # Login to Anvil

    def login(self,
              username,
              password):

        # Open a session to the Anvil and login

        self.anvil = req.Session()
        self.anvil.verify = False

        # Login to REST api

        try:
            r = self.anvil.post(self.ds_rest + "login",
                                data = { "username": username, "password": password } )
        except req.exceptions.ConnectionError as e:
            if "Connection refused" in str(e.message):
                self.logger.error("Anvil not reachable, check hostname/ip and routing")
                sys.exit(1)
            else:
                self.logger.error("Login error was: " +
                                  f"{e.args}, {e.errno}, {e.filename}, " +
                                  f"{e.message}, {e.request}, {e.response}, " +
                                  f"{e.strerror}")
                raise

        if r.status_code != 200:
            self.logger.error(f"Failed to login, HTTP code: {r.status_code}")
            sys.exit(1)

    # Get the volume and share details from the Anvil. THis routine is only done
    # when they don't know what they want by specifying the --list-volumes on the
    # command line

    def get_share_volume(self):

        # Query the anvil to get the list of volumes

        r = self.anvil.get(self.ds_rest + "storage-volumes")
        volumes_json = r.json()

        for volume in volumes_json:
            res = {}

            if volume.get('_type') == "STORAGE_VOLUME":
                res['node_name'] = volume['node']['name']
                res['name'] = volume['name']
                res['path'] = volume['logicalVolume']['exportPath']
                res['ip'] = volume['logicalVolume']['ipAddresses'][0]['address']
                res['id'] = int(volume['internalId'])

            self.volume_details.append(res)

        # Query the anvil to get the list of shares

        r = self.anvil.get(self.ds_rest + "shares")
        shares_json = r.json()

        for share in shares_json:
            res = {}
            res['path'] = share['path']
            res['id'] = int(share['internalId'])
            res['name'] = share['name']
            res['num_files'] = int(share['totalNumberOfFiles'])
            self.share_details.append(res)

    # Determine if the machine running this code is local or not

    def is_local(self,
                 target: Union[str, ipaddress.IPv4Address, ipaddress.IPv6Address],
                 logger=None) -> bool:
        
        try:

        # Convert string to IP address if necessary

            if isinstance(target, str):
                try:
                    target = ipaddress.ip_address(target)
                except ValueError:

                    # If not an IP address, try to resolve hostname

                    target = ipaddress.ip_address(socket.gethostbyname(target))
        
            return (
                target.is_private or
                target.is_loopback or
                target.is_link_local or
                str(target).startswith('127.') or
                str(target) == '::1'
            )

        except Exception as e:
            if logger is not None:
                logger.error(f"Error checking if machine is local: {e}")
            return False

    # Issue an isdir

    def isdir(self, mntdir) -> bool:

        self.logger.debug(f"Checking if {mntdir} is a directory")

        self.logger.debug("Running isdir as root")
        return os.path.isdir(mntdir)

    # Issue an mkdir

    def mkdir(self, mntdir, mode=777) -> bool:

        self.logger.debug(f"Making a directory for mounting: {mntdir}")

        return os.makedirs(mntdir, mode, exist_ok=True)

    # Unmount the share

    def umount_share_volume(self, create_dirs=False, umount_opts=""):

        for mntdir in (self.args.sharemnt, self.args.volmnt):

            new_cmd = []

            if self.isdir(mntdir):
                self.logger.debug(f"Making sure {mntdir} is not mounted" )

                cmd = "umount %s %s" % (umount_opts, mntdir)
                self.logger.debug("Attempting to unmount %s" % (mntdir))

                new_cmd = cmd.split()

                # Execute the umount command

                self.logger.debug(f"Running umount command: {new_cmd}")
                
                try:
                    result = sp.run(new_cmd, check=True, capture_output=True, text=True)
                except (Exception,) as excpt:
                    pass

                self.logger.debug(f"Finished unmounting {mntdir}")

            elif create_dirs:
                self.logger.debug(f"Making directory {mntdir}")
                self.mkdir(mntdir, mode=750)

    # Mount the volume onto a share

    def mount_share_volume(self):

        # If the directories exist, unmount them for good measure

        self.umount_share_volume(create_dirs=True, umount_opts="-f -l")

        mounts = []

        mounts.append( ( '-t nfs', "-o vers=4.2,port=20492",
                         self.args.host + ':' + self.selected_share['path'],
                         self.args.sharemnt ) )
        mounts.append( ( '-t nfs', "-o vers=3",
                         self.selected_volume['ip'] + ':' + self.selected_volume['path'],
                         self.args.volmnt ) )

        for fstype, options, path, mntdir in mounts:
            new_cmd = []
            cmd = "mount %s %s %s %s" % (fstype, options, path, mntdir)
            self.logger.debug(f"Attempting to mount {path}")

            new_cmd = cmd.split()

            # Mount the volume

            try:
                result = sp.run(new_cmd, check=True, capture_output=True, text=True)
            except (Exception,) as e:
                self.logger.error(f"Error during mount, error is: {e}")
                sys.exit(1)

            self.logger.debug(f"Finished mounting {mntdir}")


# Get arguments from command line

def commandargs(progdesc, progname, progvers):

    parser = argparse.ArgumentParser(description=progdesc)
    parser.add_argument("--version",
                         action="version",
                         version=f"{progname} - Version {progvers}")
    parser.add_argument('--host',
                        dest='host',
                        type=str,
                        default="localhost",
                        help="Hostname or IP of active Anvil node")
    parser.add_argument('--username',
                        dest='username',
                        default='admin',
                        help='User needed to login to Anvil')
    parser.add_argument('--password',
                        dest='password',
                        type=Password,
                        default=None,
                        help='Anvil password')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--list-volumes',
                       dest='list_volumes',
                       action='store_true',
                       default=False,
                       help='List available volumes and shares')
    group.add_argument('--volid',
                       '--volumeid',
                       type=int,
                       default=None,
                       help="Storage Volume ID to deassimilate to (internal id from volume-list)")
    parser.add_argument('--shareid',
                        type=int,
                        default=None,
                        help="Share ID to deassimilate to (internal id from share-list)")
    parser.add_argument('--mntdir',
                        type=str,
                        default="/mnt/deassim",
                        help="Top level directory to put mount points in")
    parser.add_argument('--numjobs',
                        type=int,
                        default=50,
                        help="Number of worker processes")
    parser.add_argument('--single-process',
                        dest='singleprocess',
                        action='store_true',
                        default=False,
                        help=argparse.SUPPRESS)
    parser.add_argument('--statistics',
                        dest='statistics',
                        action='store_true',
                        default=False,
                        help="Print out directory and file statistics")
    parser.add_argument('--totals',
                        dest='totals',
                        action='store_true',
                        default=False,
                        help="Print out directory and file totals")
    parser.add_argument('--log',
                        default='INFO',
                        required=False,
                        dest='loglevel',
                        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'DEBUG'],
                        help='Set the logging level')

    try:
        return parser.parse_args()
    except argparse.ArgumentTypeError:
        # Log an error
        sys.exit(1)
    
# Main routine...
#
# Here is where we get the arguments and then instantiate the deassimilate
# class to do the work

def main():

    # Get command line arguments

    args = commandargs(progdesc, progname, progvers)

    # Create logger

    logger = Logger(name=progname,
                    version=progvers,
                    description=progdesc,
                    level=args.loglevel)

    # Verify that the arguments are correct

    if args.volid is not None and args.shareid is None:
        logger.error("--volid requires --shareid")
    if args.shareid is not None and args.volid is None:
        logger.error("--shareid requires --volid")
    
    # Make sure that we are running as root...
    
    if not os.geteuid() == 0:
        logger.error("Must be run as root")
        sys.exit(1)

    # Create deassimilation class

    deassim = deassimilate(args, logger)

    # Setup the deassimilation class

    deassim.setup()

    # Run the deassimilation

    try:
        deassim.run()
    except KeyboardInterrupt:
        logger.info("Caught keyboard interrupt, exiting")
    except Exception as e:
        logger.error(f"Error during deassimilation: {e}")
        sys.exit(1)

    # Terminate the deassimilation

    deassim.teardown()
    
# Put in summary of results here

if __name__ == '__main__':
    main()
