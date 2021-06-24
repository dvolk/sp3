"""
catspace is a scheduled job that should run once per day
"""

import collections
import json
import logging
import pathlib
import shlex
import sqlite3
import subprocess
import time

logging.basicConfig(level=logging.DEBUG)


def get_runs_from_dir(p):
    runs = list(pathlib.Path(f"/work/{p}").glob("*"))
    return [x.stem for x in runs if x.stem != "index"]


def get_runs():
    catweb_database_file = "/db/catweb.sqlite"
    con = sqlite3.connect(catweb_database_file)
    con.row_factory = sqlite3.Row
    runs = con.execute("select * from nfruns").fetchall()
    return runs


def get_run_disk_use(pipeline_run_uuid):
    logging.info(f"get_run_disk_use({pipeline_run_uuid})")
    run_work_directory = f"/work/runs/{pipeline_run_uuid}"
    try:
        du = subprocess.check_output(["du", "-s", shlex.quote(run_work_directory)])
        du_run_space = int(du.decode().strip().split("\t")[0])
    except Exception as e:
        logging.warning(f"couldn't determine run space for {pipeline_run_uuid}:")
        logging.warning(str(e))
        du_run_space = -1

    run_output_directory = f"/work/output/{pipeline_run_uuid}"
    try:
        du = subprocess.check_output(["du", "-s", shlex.quote(run_output_directory)])
        du_output_space = int(du.decode().strip().split("\t")[0])
    except Exception as e:
        logging.warning(f"couldn't determine output space for {pipeline_run_uuid}:")
        logging.warning(str(e))
        du_output_space = -1

    return du_run_space, du_output_space


def stuff(runs):
    out = list()
    run_time = str(int(time.time()))

    for run in runs:
        run_uuid = run["run_uuid"]
        du_run_space, du_output_space = get_run_disk_use(run_uuid)
        row = dict()

        row["du_run_space"] = du_run_space
        row["du_output_space"] = du_output_space
        row["run"] = dict(run)
        out.append(row)

    return out


def emit_result(out):
    with open("/db/catspace_result.txt", "w") as f:
        f.write(json.dumps(out, indent=4))


def emit_warnings_about_missing_runs(db_runs, runs_dirs, outputs_dirs):
    db_run_uuids = set([db_run["run_uuid"] for db_run in db_runs])
    runs_dirs_uuids = set(runs_dirs)
    outputs_dirs_uuids = set(outputs_dirs)

    logging.warning(
        f"runs in /work/runs but not in database: {list(runs_dirs_uuids.difference(db_run_uuids))}"
    )
    logging.warning(
        f"runs in database but not in /work/runs: {list(db_run_uuids.difference(runs_dirs_uuids))}"
    )

    logging.warning(
        f"runs in /work/output but not in database: {list(outputs_dirs_uuids.difference(db_run_uuids))}"
    )
    logging.warning(
        f"runs in database but not in /work/output: {list(db_run_uuids.difference(outputs_dirs_uuids))}"
    )


def main():
    runs = get_runs()
    out = stuff(runs)
    emit_result(out)
    runs2 = get_runs_from_dir("runs")
    runs3 = get_runs_from_dir("output")
    emit_warnings_about_missing_runs(runs, runs2, runs3)


if __name__ == "__main__":
    main()
