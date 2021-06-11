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
    reports_db.insert( {"uuid": q[0],
                        "type": q[1],
                        "status": q[2],
                        "added_epochtime": int(q[3]),
                        "started_epochtime": int(q[4]),
                        "finished_epochtime": int(q[5]),
                        "pipeline_run_uuid": q[6],
                        "sample_name": q[7],
                        "gridfs_id": fid } )
