'''
Create symlinks for files downloaded in fetch guid X into a single directory

To run manually from the parent dir: python3 -m local1.flatten <guid> <directory>
'''

import json
import requests
import sys
import pathlib
import os
import shutil

import util
from config import config

def flatten(guid, path_root, path_suffix, logger, fetch_method):
    path_root = pathlib.Path(path_root) # symlink destination root
    path_suffix = pathlib.Path(path_suffix) # symlink destination dir

    r = requests.get("http://localhost:7200/api/fetch/status_sample/{0}".format(guid))

    j = json.loads(r.text)
    resp_data = j['data']

    if not resp_data:
        logger.warning("fetch guid {0} not found".format(guid))
        return None
    else:
        data = json.loads(resp_data[guid]['data'])

    local_dir = pathlib.Path(resp_data[guid]['name'])

    try:
        (path_root / path_suffix).mkdir(parents=True)
    except FileExistsError:
        # exist_ok added in 3.5 :(
        pass

    logger.info("symlink dir: {0}".format(str(path_root / path_suffix)))

    for src in local_dir.glob('*'):
        dest = path_root / path_suffix / src.name
        if fetch_method == 'link':
            logger.debug("symlink {0} -> {1}".format(src, dest))
            os.symlink(str(src), str(dest))
        elif fetch_method == 'copy':
            logger.debug("copy {0} -> {1}".format(src, dest))
            shutil.copyfile(str(src), str(dest))


def main():
    guid = sys.argv[1]
    path = sys.argv[2]
    path = sys.argv[3]
    flatten(guid, path_root, path_suffix)

if __name__ == '__main__':
    main()
