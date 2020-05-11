import yaml
import logging
import uuid
import pathlib
import os
import sys
import time
import sqlite3

def cmd(s):
    logging.warning(s)
    os.system(s)

def main():
    try:
        sync_conf_file = 'sync.yaml'
        f = open(sync_conf_file)
        sync_conf = yaml.load(f.read())
        output_patterns = sync_conf['output_patterns']
    except Exception as e:
        logging.error(f"Sync configuration error: {f}")
        logging.error(str(e))
        output_patterns = []

    try:
        instance_conf = pathlib.Path.home() / 'sp3' / 'instance.yaml'
        f = open(instance_conf)
    except Exception as e:
        logging.error(f"Couldn't open instance configuration file {f}")
        logging.error(str(e))
        return 1

    r = f.read()
    conf = yaml.load(r)
    instance_name = conf['name']
    instance_id = conf['id']
    store_host = conf['store']

    catweb_database_file = '/db/catweb.sqlite'

    last_synced = 0
    # get the time we last synced to this store
    try:
        with open(f"{store_host}.last") as f:
            last_synced = int(f.read())
    except Exception as e:
        print(str(e))

    print(last_synced)

    # update the last synced time to this time
    now = str(int(time.time()))

    # get guids for successfully finished runs that have started since we last synced
    con = sqlite3.connect(catweb_database_file)
    runs = con.execute("select run_uuid from nfruns where status = 'OK' and cast(start_epochtime as integer) > ?", (last_synced,)).fetchall()
    runs = [x[0] for x in runs]

    local_outputs = [f"/work/output/{run}" for run in runs]
    local_runs = [f"/work/runs/{run}" for run in runs]

    local_files_abs = [str(instance_conf)]
    local_files_rel = ['/db/catweb.sqlite',
                       '/db/catreport.sqlite',
                       '/work/reports/catreport/reports']

    local_files_rel += local_runs

    # abs files: /a/b/c -> /persistence/{instance_id}/c
    # rel files: /a/b/c -> /persistence/{instance_id}/a/b/c

    cmd(f"rsync            -a {' '.join(local_files_abs)} {store_host}:/work/persistence/{instance_id}/")
    # TODO chunk local_files_rel in case it's too big
    cmd(f"rsync --relative -a {' '.join(local_files_rel)} {store_host}:/work/persistence/{instance_id}/")

    # selectively sync output files (fasta and vcf files etc)
    if local_outputs and output_patterns:
        includes_files = ' '.join(['--include \'' + include + '\'' for include in output_patterns])
        # include directories, include files, exclude everything else
        includes_str = f"--include '*/' {includes_files} --exclude '*'"
        local_outputs_str = ' '.join(local_outputs)
        cmd(f"rsync --relative -a  {includes_str} {local_outputs_str} {store_host}:/work/persistence/{instance_id}/")

    # write new last synced time
    with open(f"{store_host}.last", "w") as f:
        f.write(str(int(time.time())))

    return 0

if __name__ == '__main__':
    exit(main())
