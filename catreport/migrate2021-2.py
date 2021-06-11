import uuid
import sqlite3
import pymongo
import gridfs

con = sqlite3.connect("/db/catreport.sqlite")

myclient = pymongo.MongoClient("mongodb://localhost:27017/")
mydb = myclient["catreport"]
fs = gridfs.GridFS(mydb)
reports_db = mydb["reports"]

for q in con.execute("select * from q"):
    print(f"processing {q}")
    f = f"/work/reports/catreport/reports/{q[0][0:2]}/{q[0][2:4]}/{q[0]}.json"
    try:
        contents = open(f, "rb").read()
        fid = fs.put(contents, filename=q[0])
    except:
        print(f"warning: couldn't read {f}")
        fid = None

    try:
        added_epochtime = int(q[3])
    except:
        added_epochtime = 0
    try:
        started_epochtime = int(q[4])
    except:
        started_epochtime = 0
    try:
        finished_epochtime = int(q[5])
    except:
        finished_epochtime = 0

    reports_db.insert( {"uuid": q[0],
                        "type": q[1],
                        "status": q[2],
                        "added_epochtime": added_epochtime,
                        "started_epochtime": started_epochtime,
                        "finished_epochtime": finished_epochtime,
                        "pipeline_run_uuid": q[6],
                        "sample_name": q[7],
                        "gridfs_id": fid } )
