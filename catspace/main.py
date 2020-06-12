"""
catspace is a scheduled job that should run once per day
"""

import collections
import sqlite3
import time
import subprocess
import shlex
import logging
import json

logging.basicConfig(level=logging.DEBUG)

def get_runs():
    catweb_database_file = '/db/catweb.sqlite'
    con = sqlite3.connect(catweb_database_file)
    con.row_factory = sqlite3.Row
    runs = con.execute("select * from nfruns where status = 'OK'").fetchall()
    return runs

def get_run_disk_use(pipeline_run_uuid):
    logging.info(f"get_run_disk_use({pipeline_run_uuid})")
    run_work_directory = f"/work/runs/{pipeline_run_uuid}"
    try:
        du = subprocess.check_output(["du", "-s", shlex.quote(run_work_directory)])
        du_run_space = int(du.decode().strip().split('\t')[0])
    except Exception as e:
        logging.warning(f"couldn't determine run space for {pipeline_run_uuid}:")
        logging.warning(str(e))
        du_run_space = -1

    run_output_directory = f"/work/output/{pipeline_run_uuid}"
    try:
        du = subprocess.check_output(["du", "-s", shlex.quote(run_output_directory)])
        du_output_space = int(du.decode().strip().split('\t')[0])
    except:
        logging.warning(f"couldn't determine output space for {pipeline_run_uuid}:")
        logging.warning(str(e))
        du_output_space = -1

    return du_run_space, du_output_space

def stuff(runs):
    out = list()
    run_time = str(int(time.time()))

    for run in runs:
        run_uuid = run['run_uuid']
        du_run_space, du_output_space = get_run_disk_use(run_uuid)
        row = dict()

        row['du_run_space'] = du_run_space
        row['du_output_space'] = du_output_space
        row['run'] = dict(run)
        out.append(row)

    return out

def emit_result(out):
    with open("/db/catspace_result.txt", "w") as f:
        f.write(json.dumps(out, indent=4))

def main():
    runs = get_runs()
    out = stuff(runs)
    emit_result(out)

if __name__ == '__main__':
    main()
