import copy
import json
import logging
import sqlite3
import time
import uuid
import collections

import gridfs
import pymongo

myclient = pymongo.MongoClient("mongodb://localhost:27017/")
mydb = myclient["catweb"]
fs = gridfs.GridFS(mydb)
nfruns_db = mydb["nfruns"]
nftraces_db = mydb["traces"]
reference_cache_db = mydb["reference_cache"]
forum_post_cache = mydb["forum_post_cache"]


def add_to_reference_cache(ref_uuid, reference_json):
    reference_cache_db.insert({"uuid": ref_uuid, "reference_json": reference_json})


def get_reference_cache(ref_uuid):
    r = reference_cache_db.find_one({"uuid": ref_uuid})
    if r:
        return r.get("reference_json")


def get_status(org, is_admin):
    logging.warning(f"get_status({org}, {is_admin})")
    if is_admin:
        running = (
            nfruns_db.find({"status": "-"}, {"_id": 0})
            .sort("start_epochtime", -1)
            .limit(5)
        )
        recent = (
            nfruns_db.find({"status": "OK"}, {"_id": 0})
            .sort("start_epochtime", -1)
            .limit(5)
        )
        failed = (
            nfruns_db.find({"status": "ERR"}, {"_id": 0})
            .sort("start_epochtime", -1)
            .limit(5)
        )
    else:
        org_search = {"$regex": f"^{org}-.*"}
        running = (
            nfruns_db.find({"status": "-", "workflow": org_search}, {"_id": 0})
            .sort("start_epochtime", -1)
            .limit(5)
        )
        recent = (
            nfruns_db.find({"status": "OK", "workflow": org_search}, {"_id": 0})
            .sort("start_epochtime", -1)
            .limit(5)
        )
        failed = (
            nfruns_db.find({"status": "ERR", "workflow": org_search}, {"_id": 0})
            .sort("start_epochtime", -1)
            .limit(5)
        )

    return (
        [run_to_old_format(run) for run in running],
        [run_to_old_format(run) for run in recent],
        [run_to_old_format(run) for run in failed],
    )


def run_to_old_format(run):
    return [
        run["date_time"],
        run["duration"],
        run["code_name"],
        run["status"],
        run["hash"],
        run["uuid"],
        run["command_line"],
        run["user"],
        run["sample_group"],
        run["workflow"],
        run["context"],
        run["root_dir"],
        run["output_arg"],
        run["output_dir"],
        run["run_uuid"],
        run["start_epochtime"],
        run["pid"],
        run["ppid"],
        run["end_epochtime"],
        run["output_name"],
        run["data_json"],
    ]


def get_workflow(flow_name):
    # deprecated
    runs = nfruns_db.find({"workflow": flow_name}).sort("start_epochtime", -1)
    ret = list()
    for run in runs:
        ret.append(run_to_old_format(run))
    return ret


def get_pipeline_runs(flow_name):
    # aka get_workflow with new format
    return list(
        nfruns_db.find({"workflow": flow_name}, {"_id": 0}).sort("start_epochtime", -1)
    )


def delete_run(run_uuid):
    nfruns_db.delete_one({"run_uuid": run_uuid})


def get_run(run_uuid):
    # deprecated
    run = nfruns_db.find_one({"run_uuid": run_uuid})
    return [run_to_old_format(run)]


def get_pipeline_run(run_uuid):
    # aka get_run with new format
    return nfruns_db.find_one({"run_uuid": run_uuid}, {"_id": 0})


def insert_files_table(run_uuid, input_files_count, input_files):
    nfruns_db.update(
        {"run_uuid": run_uuid},
        {"$set": {"input_files_count": input_files_count, "input_files": input_files}},
    )


def get_input_files_count(run_uuid):
    r = nfruns_db.find_one({"run_uuid": run_uuid}, {"input_files_count": 1})

    return r.get("input_files_count", -1), -1


def get_run_and_status(pipeline_name):
    r = list(nfruns_db.find({"workflow": pipeline_name}, {"run_uuid": 1, "status": 1}))
    status_to_run_uuid = collections.defaultdict(list)
    run_uuid_to_status = dict()
    for x in r:
        status_to_run_uuid[x["status"]].append(x["run_uuid"])
        run_uuid_to_status[x["run_uuid"]] = x["status"]
    return { "status_to_run_uuid": status_to_run_uuid,
             "run_uuid_to_status": run_uuid_to_status }


def insert_dummy_run(data):
    data2 = copy.deepcopy(data)
    data2.pop("flow_cfg", None)
    # insert a dummy entry into the table so that the user sees that a run is starting
    # this is replaced when the nextflow process starts
    nfruns_db.insert(
        {
            "date_time": time.strftime("%Y-%m-%d %H:%M:%S"),
            "duration": "-",
            "code_name": "-",
            "status": "STARTING",
            "hash": "-",
            "uuid": "-",
            "command_line": "-",
            "user": data["user_name"],
            "sample_group": "",
            "workflow": data["flow_cfg"]["name"],
            "context": data["context"],
            "root_dir": "-",
            "output_arg": "-",
            "output_dir": "-",
            "run_uuid": data["run_uuid"],
            "start_epochtime": str(int(time.time())),
            "pid": "-",
            "ppid": "-",
            "end_epochtime": str(int(time.time())),
            "output_name": data["run_name"],
            "data_json": json.dumps(data2),
        }
    )


def insert_run(s, run_uuid):
    nfruns_db.update(
        {"run_uuid": run_uuid},
        {
            "$set": {
                "date_time": s[0],
                "duration": s[1],
                "code_name": s[2],
                "status": s[3],
                "hash": s[4],
                "uuid": s[5],
                "command_line": s[6],
                "user": s[7],
                "sample_group": s[8],
                "workflow": s[9],
                "context": s[10],
                "root_dir": s[11],
                "output_arg": s[12],
                "output_dir": s[13],
                "run_uuid": s[14],
                "start_epochtime": s[15],
                "pid": s[16],
                "ppid": s[17],
                "end_epochtime": s[18],
                "output_name": s[19],
                "data_json": s[20],
            }
        },
    )


def load_nextflow_trace(pipeline_run_uuid):
    r = nftraces_db.find_one(
        {"pipeline_run_uuid": pipeline_run_uuid}, {"nextflow_trace_content": 1}
    )
    if not r:
        return ""
    return r.get("nextflow_trace_content", "")


def save_nextflow_trace(pipeline_run_uuid, trace_content):
    nftraces_db.replace_one(
        {"pipeline_run_uuid": pipeline_run_uuid},
        {
            "pipeline_run_uuid": pipeline_run_uuid,
            "nextflow_trace_content": trace_content,
        },
        upsert=True,
    )


def save_nextflow_file(pipeline_run_uuid, f, filename):
    if filename == "report.html":
        db_filename = f"nextflow.report_html.{pipeline_run_uuid}"
    elif filename == "timeline.html":
        db_filename = f"nextflow.timeline_html.{pipeline_run_uuid}"
    elif filename == ".nextflow.log":
        db_filename = f"nextflow.timeline_html.{pipeline_run_uuid}"
    else:
        return None
    return fs.put(f, filename=db_filename)


def load_nextflow_file(pipeline_run_uuid, filename):
    if filename == "report.html":
        db_filename = f"nextflow.report_html.{pipeline_run_uuid}"
    elif filename == "timeline.html":
        db_filename = f"nextflow.timeline_html.{pipeline_run_uuid}"
    else:
        return None
    r = fs.find_one({"filename": db_filename}).read()
    if not r:
        logging.warning(f"gridfs file {db_filename} not found")
        return None
    try:
        return r.decode()
    except:
        return r


def nextflow_file_exists(pipeline_run_uuid, filename):
    if filename == "report.html":
        db_filename = f"nextflow.report_html.{pipeline_run_uuid}"
    elif filename == "timeline.html":
        db_filename = f"nextflow.timeline_html.{pipeline_run_uuid}"
    else:
        return None
    if fs.find_one({"filename": db_filename}):
        return True
    else:
        return False


def search_for_input_sample(sample_part, org, is_admin=False):
    return_fields = {"_id": 0}
    sample_regex = {"$regex": f".*{sample_part}.*"}
    try:
        if is_admin:
            # admins can list all runs
            rows = list(
                nfruns_db.find({"input_files": sample_regex}, return_fields)
                .sort("start_epochtime", -1)
                .limit(100)
            )
        else:
            # other users can only see runs in their organisation
            org_search = {"$regex": f"^{org}-.*"}
            rows = (
                nfruns_db.find(
                    {"input_files": sample_regex, "workflow": org_search}, return_fields
                )
                .sort("start_epochtime", -1)
                .limit(100)
            )
    except Exception as e:
        logging.error(str(e))
        return str(e)

    return rows


def forum_set_post_cache(title, content):
    cache_uuid = str(uuid.uuid4())
    forum_post_cache.insert({"uuid": cache_uuid, "title": title, "content": content})
    return cache_uuid


def forum_get_post_cache(cache_uuid):
    ret = forum_post_cache.find_one({"uuid": cache_uuid})
    if ret:
        return ret["title"], ret["content"]
    else:
        return "", ""
