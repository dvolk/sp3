import json
import time
import uuid
import pathlib
import os
import threading
import logging
import datetime

import requests
import flask
from flask import request
import yaml
import waitress

import pymongo
import gridfs

import resistance_help
import getreportlib

app = flask.Flask(__name__)

def epochtime():
    return str(int(time.time()))

myclient = pymongo.MongoClient("mongodb://localhost:27017/")
mydb = myclient["catreport"]
fs = gridfs.GridFS(mydb)
reports_db = mydb["reports"]

# ---------------------------------------------------------------------------
# mongodb

def db_insert_new(d):
    reports_db.insert(d)

def db_get_report_for_type(pipeline_run_uuid, sample_name, report_type):
    return reports_db.find_one({ "status": "done",
                                 "pipeline_run_uuid": pipeline_run_uuid,
                                 "sample_name": sample_name,
                                 "type": report_type }, sort=[("added_epochtime", pymongo.DESCENDING)])

def db_get_queue(report_type):
    return reports_db.find({ "status": "queued",
                             "type": report_type }, sort=[("added_epochtime", pymongo.DESCENDING)])

def db_update_report_result(report_started_epochtime, report_finished_epochtime, report_status, report_uuid, gid):
    reports_db.update({ "uuid": report_uuid },
                      { "$set": { "started_epochtime": report_started_epochtime,
                                  "finished_epochtime": report_finished_epochtime,
                                  "status": report_status,
                                  "gid": gid }})

def save_report_file(report_uuid, report_content):
    logging.warning(f"save_report_file({report_uuid}, len: {len(report_content)})")
    # write to file as backup and diagnostic
    prefix = pathlib.Path(f"/work/reports/catreport/reports/{report_uuid[0:2]}/{report_uuid[2:4]}/")
    if not prefix.exists():
        prefix.mkdir()
    with open(prefix / report_uuid, "w") as f:
        f.write(report_content)
    # main storage on mongodb gridfs
    gid = fs.put(report_content.encode(), filename=report_uuid)
    return gid

# ---------------------------------------------------------------------------
# make report functions

def report_thread_factory(report_type, make_report_function):
    logging.warning(f"starting thread for {report_type}")
    while True:
        rows = list(db_get_queue(report_type))
        for row in rows:
            logging.warning(row)
            a = datetime.datetime.now()
            report_started_epochtime = epochtime()
            logging.warning(f"thread {report_type}: working on run {row['pipeline_run_uuid']} sample ({row['sample_name']})")
            report_content = make_report_function(row['uuid'],
                                                  row['sample_filepath'],
                                                  row['sample_name'],
                                                  row['pipeline_run_uuid'])
            gid = save_report_file(row['uuid'], report_content)
            report_status = 'done'
            report_finished_epochtime = epochtime()
            db_update_report_result(report_started_epochtime,
                                    report_finished_epochtime,
                                    report_status,
                                    row['uuid'],
                                    gid)
            b = datetime.datetime.now()
            logging.warning(f"thread {report_type}: finished run {row['pipeline_run_uuid']} sample ({row['sample_name']}) in {(b-a).total_seconds()} s")
        time.sleep(15)

def make_trivial_copy_report(report_uuid, sample_filepath, sample_name, pipeline_run_uuid):
    with open(sample_filepath, "rb") as f:
        try:
            return f.read().decode()
        except:
            return f.read()

def make_within_run_distreport(report_uuid, sample_filepath, sample_name, pipeline_run_uuid):
    os.system(f"python3 distmatrixsp3input.py /work/output/{pipeline_run_uuid} | python3 distmatrix.py > /tmp/distreport_{report_uuid}.txt")
    with open(f"/tmp/distreport_{report_uuid}.txt") as f:
        return f.read()

def make_resistance_report(report_uuid, sample_filepath, sample_name, pipeline_run_uuid):
    '''
    1. symlink sample file path to /work/reports/resistanceapi/vcfs/{report_uuid}.vcf
    2. send request for report to resistance api
    3. write report to /work/reports/catreport/reports/{report_uuid}.json
    4. delete symlink from 1.
    '''
    os.system(f'cd /work/reports/resistanceapi/vcfs; ln -s {sample_filepath} {report_uuid}.vcf')
    url = f'http://localhost:8990/api/v1/resistances/piezo/{report_uuid}?type=piezo'
    logging.warning(f"resistance api: {url}")
    r = requests.get(url)
    return r.text

# ---------------------------------------------------------------------------
# web api

@app.route('/req_report/', methods=['POST'])
def req_report():
    '''
    Request a report

    It is added to the queue and processed one by one

    Mandatory inputs: pipeline run uuid, sample name, sample path, report type
    '''
    logging.warning(request.data)
    data = json.loads(request.data.decode('utf-8'))
    pipeline_run_uuid = data['pipeline_run_uuid']
    sample_name = data['sample_name']
    sample_filepath = data['sample_filepath']
    report_type = data['report_type']

    report_uuid = str(uuid.uuid4())
    report_status = 'queued'
    report_added_epochtime = epochtime()

    report_started_epochtime = str()
    report_finished_epochtime = str()
    report_filename = str()
    software_versions = str()

    new_doc = { "uuid": report_uuid,
                "type": report_type,
                "status": report_status,
                "added_epochtime": report_added_epochtime,
                "started_epochtime": report_started_epochtime,
                "report_finished_epochtime": report_finished_epochtime,
                "pipeline_run_uuid": pipeline_run_uuid,
                "sample_name": sample_name,
                "sample_filepath": sample_filepath,
                "report_filename": report_filename,
                "software_versions": software_versions }
    db_insert_new(new_doc)

    return "queued"

@app.route('/report/<pipeline_run_uuid>/<sample_name>')
def get_report(pipeline_run_uuid, sample_name):
    return json.dumps(getreportlib.get_report(reports_db, fs, pipeline_run_uuid, sample_name))

def main():
    threading.Thread(target=report_thread_factory, args=("resistance", make_resistance_report)).start()
    threading.Thread(target=report_thread_factory, args=("mykrobe_speciation", make_trivial_copy_report)).start()
    threading.Thread(target=report_thread_factory, args=("kraken2_speciation", make_trivial_copy_report)).start()
    threading.Thread(target=report_thread_factory, args=("pick_reference", make_trivial_copy_report)).start()
    threading.Thread(target=report_thread_factory, args=("samtools_qc", make_trivial_copy_report)).start()

    threading.Thread(target=report_thread_factory, args=("nfnvm_nanostats_qc", make_trivial_copy_report)).start()
    threading.Thread(target=report_thread_factory, args=("nfnvm_kronareport", make_trivial_copy_report)).start()
    threading.Thread(target=report_thread_factory, args=("nfnvm_flureport", make_trivial_copy_report)).start()
    threading.Thread(target=report_thread_factory, args=("nfnvm_viralreport", make_trivial_copy_report)).start()
    threading.Thread(target=report_thread_factory, args=("nfnvm_map2coverage_report", make_trivial_copy_report)).start()

    threading.Thread(target=report_thread_factory, args=("nfnvm_resistance", make_trivial_copy_report)).start()

    threading.Thread(target=report_thread_factory, args=("run_distmatrix", make_within_run_distreport)).start()

    waitress.serve(app, listen='127.0.0.1:10000')

if __name__ == '__main__':
    main()
