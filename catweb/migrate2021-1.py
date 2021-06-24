import copy
import json
import sqlite3
import sys

import pymongo

myclient = pymongo.MongoClient("mongodb://localhost:27017/")
mydb = myclient["catweb"]
nfruns_db = mydb["nfruns"]
nftraces_db = mydb["traces"]

con = sqlite3.connect("/db/catweb.sqlite")
con.row_factory = sqlite3.Row

nfruns = con.execute("select * from nfruns").fetchall()
nffiles = con.execute("select * from nffiles").fetchall()

nffiles_d = {row["uuid"]: dict(row) for row in nffiles}
out = list()

for run in nfruns[2:]:
    row = copy.copy(dict(run))
    uuid = row["run_uuid"]

    row["input_files"] = nffiles_d.get(uuid, dict()).get("input_files", list())
    row["input_files_count"] = nffiles_d.get(uuid, dict()).get("input_files_count", -1)
    try:
        with open(f"/work/runs/{uuid}/trace.txt") as f:
            trace = f.read()
    except:
        print(f"missing trace: {uuid}")
        trace = ""

    nfruns_db.insert(row)
    nftraces_db.insert(
        {"pipeline_run_uuid": row["run_uuid"], "nextflow_trace_content": trace}
    )

    sys.stdout.write(".")
print("")
