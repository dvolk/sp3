'''
Create symlinks for files downloaded in fetch guid X into a single directory

To run manually from the parent dir: python3 -m ena.flatten <guid> <directory>
'''

import json
import requests
import sys
import pathlib
import os

import util
from config import config

def flatten(guid, path_root, path_suffix, logger):
    path_root = pathlib.Path(path_root)
    path_suffix = pathlib.Path(path_suffix)

    r = requests.get("http://localhost:7200/api/fetch/status_sample/{0}".format(guid))

    j = json.loads(r.text)
    resp_data = j['data']

    if not resp_data:
        logger.warning("fetch guid {0} not found".format(guid))
        return None
    else:
        data = json.loads(resp_data[guid]['data'])

    ena_download_dir = pathlib.Path(config.get("ena_download_dir"))

    try:
        (path_root / path_suffix).mkdir(parents=True)
    except FileExistsError:
        # exist_ok added in 3.5 :(
        pass

    logger.info("symlink dir: {0}".format(str(path_root / path_suffix)))

    for f in data['ok_download_files']:
        ena_path = pathlib.Path(f.replace('ftp.sra.ebi.ac.uk/', ''))

        src = ena_download_dir / ena_path
        dest = path_root / path_suffix / ena_path.name

        logger.debug("symlink -> {1}".format(src, dest))
        os.symlink(str(src), str(dest))

def main():
    guid = sys.argv[1]
    path = sys.argv[2]
    path = sys.argv[3]
    flatten(guid, path_root, path_suffix)

if __name__ == '__main__':
    main()
