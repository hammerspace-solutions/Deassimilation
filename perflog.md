# 20171013 / 20d30b415ca7b06e03d2003ff10dc186104ad9a1

Symlinks not supported version, Running standard 1 million files workload

Standard numbjobs 128, run on ds1.ap.omner.org and dsxt3.ap.omner.org with no
other items active.

19m39s or 848 files per second.

# 20171016 / c18977327b7a1b1a3dff05e15ec7173f0619eaf3

Symlinks supported version, more individual metadata ops.  Same system config
as 20171013 run but add 5 symlink files.  

run1: 24m17s or 686 files per second
run2: 23m59s or 695 files per second

rm -rf time: 14m32s

This newer version does a lot more logging, sufficient to fix any file /
symlink and metadata manually.  Also now avoiding the shutil metadata copy
helpers and directly calling the metadata ops directly, this could also be
adding to the slowdown.

# 20171025 / 6ebab3abc2dbdd2dbb6251ab391be4192c7a43ae

Work around race condition inside python with callback by adding delay in pool workers
Added ability to restart assimilation half way through, ignores and logs existing files

run1 (full create): 25m4s or 664 files per second
run2 (all files exist): 23m49s
