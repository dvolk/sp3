import pymongo, gridfs, argh

def go():
    myclient = pymongo.MongoClient("mongodb://localhost:27017/")
    mydb = myclient["catreport"]
    fs = gridfs.GridFS(mydb)
    reports_db = mydb["reports"]

    uuids = list(reports_db.find({}, { "_id": 0, "uuid": 1 }))
    uuids = [x["uuid"] for x in uuids]
    print(len(uuids))

    for uuid in uuids:
        print(uuid)
        files = list(fs.find({ "filename": uuid }))
        removed = 0
        for file in files[1:]:
            fs.delete(file._id)
            removed = removed + 1
        print(removed)

if __name__ == "__main__":
    argh.dispatch_command(go)
