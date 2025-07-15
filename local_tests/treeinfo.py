#!/usr/bin/env python3
#
# Walk a hammerspace namespace and report stats on the files contained in there
#
from __future__ import print_function

import os, sys
import logging as log
import argparse
import pdctk.pdirwalk as pdirwalk
import stat
import json
import time

class RPStats(pdirwalk.ResultsProcessor):
    def _setup(self):
        self.per_obs = {}
        self.zero_size = 0
        self.not_file = 0
        self.reg_file = 0
        self.dirs = 0

        self.run_count = 0

    def _process(self, res):
        self.dirs += 1
        self.zero_size += res['zero-size']
        self.not_file += res['not-file']
        self.reg_file += res['reg-file']
        for obs in res['obs']:
            self.per_obs.setdefault(obs, 0)
            self.per_obs[obs] += 1

        if self.run_count % 1000 == 0:
            print("")
            print(str(self))
            print("")
            
        self.run_count += 1

    def __str__(self):
        ret = "zero_size: %d\n" % self.zero_size
        ret += "not_file: %d\n" % self.not_file
        ret += "dirs: %d\n" % self.dirs
        ret += "reg files: %d\n" % self.reg_file
        for obs, cnt in self.per_obs.items():
            ret += "obs %d: %d\n" % (obs, cnt)
        return ret
    
    def _get_results(self):
        ret = {}
        for attr in ( 'per_obs', 'zero_size', 'not_file', 'reg_file', 'dirs', ):
            ret[attr] = getattr(self, attr)
        return ret
        

def retryopen(fpath):
    # Work around instability of shadow files in 4.1 and earlier
    opencnt = 0
    opensuccess = False
    while not opensuccess and opencnt < 3:
        try:
            fd = open(fpath)
        except FileNotFoundError:
            time.sleep(.1)
        else:
            opensuccess = True
        finally:
            opencnt += 1

    if not opensuccess:
        raise FileNotFoundError(fpath)
    return fd


def shadfile(fpath, ret):
       
    with retryopen(fpath + "?.attribute=inode_info") as fd:
        jdata = json.load(fd)

    if jdata['size'] == 0:
        ret['zero-size'] += 1
    if 'instance' in jdata:
        for instance in jdata['instance']:
            ret['obs'].append(instance['obs'])
    if 'archive' in jdata:
        for archive in jdata['archive']:
            ret['obs'].append(archive['obs'])
    return ret

def getstats_dir(proc_id, static_args, work_id, share_path, filenames):
    log_header = "P%03d W%05d " % (proc_id, work_id)
    
    ret = { 
        'obs': [],
        'zero-size': 0,
        'not-file': 0,
        'reg-file': 0,
    }

    for fn in filenames:
        fpath = os.path.join(share_path, fn)
        file_stat = os.lstat(fpath)
        filetype = pdirwalk.get_filetype(file_stat)

        if filetype == "REGULAR":
            shadfile(fpath, ret)
            ret['reg-file'] += 1
        elif filetype == "SYMLINK":
            ret['not-file'] += 1
        elif filetype == "DIR":
            # this shouldn't happen
            raise RuntimeError('processing directory as file %s' % (fpath))
        else:
            ret['not-file'] += 1

    static_args.q.put(ret)

    return work_id
    

def main():
    log.basicConfig(filename="treeinfo.log")
    log.getLogger().setLevel(log.DEBUG)

    p = argparse.ArgumentParser("Report details on the specified path")
    p.add_argument('path', type=str, help="root path to collect stats on")
    args = p.parse_args()

    rp = RPStats()
    pdirwalk.pdirwalk(args.path, getstats_dir, results_processor=rp)
    print("")
    print(json.dumps(rp.final_results, sort_keys=True, indent=4))
    

if __name__ == '__main__':
    main()
