# WARNINGS

This script sets up NFS mounts and must be run as root and have RW access to
both the DataSphere share and the storage volume share.

It should not be run on the DataSphere or DSX nodes directly.
Please run it on a throw away NFS 4.2 capable client, container or VM are
great.

If running deassim against an active production system, be mindful of
the number of jobs launched in parallel with the --numjobs flag.  Script
defaults to 128 outstanding operations.  This could adversely affect other
client's latency on either the DataSphere OR the V3 storage volume system.  If
in doubt, do some short test runs and find an optimal --numjobs.


# Install dependencies:

* Debian Stretch (9): sudo apt-get install python-requests-toolbelt
* RHEL/Centos 7: ???

# Running

The only required parameter is "--ds <datasphere_hostname_or_ip>" everything
else will be looked up and prompted for.
```
sudo ./deassimilate.py --ds example.org
```

To run in a more automated fashion, the minimum set of command line arguments
are the following.  volid and shareid can be found using share-list and
volume-list as an Admin user on the DataSphere ssh cli, or by running the
script and noting the choices made.
```sh
sudo ./deassimilate.py --ds example.org --authfile auth --volid 10 --shareid 3
```

There are other options as well.  See the --help output for more control over the process.

While the script is operating it will output a stream of status characters
similar to "s-s+ss-s-++sssssssssss-s-++ss---s-+-".
* +: Additional directory queued for the worker pool to process
* -: Queued directory completed processing
* s: Maximum amount of work already queued, not doing any work this cycle


# Sample auth file
The auth file is just a text file with the DataSphere username on the first
line and password on the second line.  On a clean install the file would look like this:

```
admin
admin
```


# Post deassimilation

XXX Add verify steps

XXX Add big warning and data deletion step


# Limitations

Can't set the ctime for any files. Not allowed by system API.  atime/mtime are replicated.
* Unix ctime = metadata last change time
* Windows ctime = file create time

Can't set atime/mtime on symlinks.  Not allowed by system API, no lutime

Can't set mode bits (permissions) specific to symlinks under linux.  All symlinks are lrwxrwxrwx

# TODO
* Verify only mode
  * Stage 1 verification, compare two live trees, filenames, types, attributes, etc.
  * Stage 2 verification, log all files / attributes / etc, able to run
    verification after the original files (assim verify) or the PrimaryData
    directory (deassim) is deleted
  * Stage 3 verification, Don't get blamed in the future for existing data corruption.
    * Make sure files are readable,
    * log checksums of all files.
    * Should work only in instance files, or on source files post assimilation
      completion.
    * Make sure to restore atime after reading.
* Support attributes (lsattr)?  Getting error from lsattr on DataSphere NFSv4.2 mount...  Or on DSXv3 mount.
  * lsattr: Inappropriate ioctl for device While reading flags on dir00000000/dir00000000/file00000001
* Windows Support
  * Setting Windows ACE / ACLs, use smbcacls
  * Windows special link file type?  Will these just work?
  * Other?
* Finish up the 'fixup' generator.  Generate a shell script that will fix up
  any items that had errors on initial pass without having to do full deassim
  pass.
* Support 'other' file types
  * Device files (char / block)
  * Pipe files
  * Socket files
* Harden main code path
  * Catch exceptions, log and retry
    * os.link, os.symlink, os.lstat, os.readlink, os.lchown, os.chmod, os.utime
  * Troublesome NFS servers (DataSphere and V3)
    * Fail to mount
    * Only allow RO access
    * Not resonding
    * Network down mid test
    * Slow
* Testing
  * Need to test against larger file sets (1 million tested so far)
  * Test with 'funky' character names
  * Can just a subtree of a share be deassimilated?
* Generate 'cleanup' script to unmount the file systems and remove the mount directories.  Also for use with fixup and setup scripts.
* Generate 'setup' script to create the mount directories and mount the file system (for use with fixup script)
* Characterize likely hood of DOSing the DataSphere or the storage volume with default 128 worker jobs
* during run files+dirs/s stats
* post run perf stats summary
* post run error summary


# Done

* Basic Functionality of deassim of normal from any v4.2 supported client
* Integrate directly with DataSphere for needed config data
* Easy to use UI, only requires end user pass in target DataSphere host name, prompts for remainder of needed details
* Power user UI, all options allowed to be set by command line for no interaction
  * $ sudo ./deassimilate.py --ds ds.example.org --authfile auth --volid 10 --shareid 3
* Strict root only permissions on temporary mount directories
* Support Symlinks
