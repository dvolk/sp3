import json
import time
import uuid
import sqlite3
import pathlib
import os
import threading
import logging

import requests
import flask
from flask import request
import yaml

import resistance_help
import getreportlib

with open('catreport.yaml') as f:
    config = yaml.load(f.read())

app = flask.Flask(__name__)

def epochtime():
    return str(int(time.time()))

con = sqlite3.connect(config['db_target'], check_same_thread=False)
con.execute('create table if not exists q (uuid primary key, type, status, added_epochtime, started_epochtime, finished_epochtime, pipeline_run_uuid, sample_name, sample_filepath, report_filename, software_versions)')
con.execute('create index if not exists q_pipeline_uuids on q (pipeline_run_uuid)')
con.execute('create index if not exists q_type on q (type)')
con.execute('create index if not exists q_status on q (status)')

sql_lock = threading.Lock()

def db_insert_new(new_row):
    with sql_lock, con:
        con.execute('insert into q values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', new_row)

def db_get_report_for_type(cluster_instance_uuid, pipeline_run_uuid, sample_name, report_type):
    with sql_lock, con:
        r = con.execute('select * from q where status = "done" and pipeline_run_uuid = ? and sample_name = ? and type = ? order by added_epochtime desc',
                        (pipeline_run_uuid, sample_name, report_type)).fetchall()
    if r:
        return r[0]
    else:
        return None

def db_get_queue(con, report_type):
    with sql_lock, con:
        rows = con.execute("select * from q where status = 'queued' and type = ? order by added_epochtime desc limit 1", (report_type,)).fetchall()
    return rows

def db_update_report_result(con, report_filename, report_started_epochtime, report_finished_epochtime, report_status, report_uuid):
    with sql_lock, con:
        con.execute("update q set report_filename = ?, started_epochtime = ?, finished_epochtime = ?, status = ? where uuid = ?",
                    (report_filename, report_started_epochtime, report_finished_epochtime, report_status, report_uuid ))

def db_get_queued_report_count(con, report_type):
    with sql_lock, con:
        rows = con.execute("select count(*) from q where type = ? and status = 'queued'", (report_type,)).fetchone()
    return rows

@app.route('/list_reports/')
def list_report():
    '''
    List the last 1000 resistance reports in the queue
    '''
    data = []
    detail = None
    try:
        data = db_get_reports(con, 'resistance')
        status = 'success'
        detail = str(len(data))
    except:
        status = 'failed'
    return json.dumps({ 'status': status,
                        'details': detail,
                        'data': data })

@app.route('/req_report/', methods=['POST'])
def req_report():
    '''
    Request a report

    It is added to the queue and processed one by one

    Mandatory inputs: pipeline run uuid, sample name, sample path, report type
    '''
    print(request.data)
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

    new_row = (report_uuid, report_type, report_status, report_added_epochtime, report_started_epochtime,
               report_finished_epochtime, pipeline_run_uuid, sample_name, sample_filepath, report_filename, software_versions)
    db_insert_new(new_row)

    return "queued"

def report_thread_factory(con, report_type, make_report_function):
    print(f"starting thread for {report_type}")
    while True:
        rows = db_get_queue(con, report_type)
        if rows:
            row = rows[0]
            report_uuid = row[0]
            sample_filepath = row[8]
            sample_name = row[7]
            pipeline_run_uuid = row[6]

            report_started_epochtime = epochtime()
            print(f"{report_type}_thread: working on {report_uuid} ({sample_filepath})")
            report_filename = make_report_function(report_uuid, sample_filepath, sample_name, pipeline_run_uuid)
            print(f"{report_type}_thread: finished with {report_uuid}")
            report_status = 'done'
            report_finished_epochtime = epochtime()
            db_update_report_result(con, report_filename, report_started_epochtime, report_finished_epochtime, report_status, report_uuid)

        time.sleep(1)

def get_report_for_type(pipeline_run_uuid, sample_name, report_type):
    '''
    Query database for report

    Mandatory inputs: pipeline run uuid, sample name, report type
    '''
    return db_get_report_for_type(con, pipeline_run_uuid, sample_name, report_type)

def make_within_run_distreport(report_uuid, sample_filepath, sample_name, pipeline_run_uuid):
    os.system(f"python3 distmatrixsp3input.py /work/output/{pipeline_run_uuid} | python3 distmatrix.py > /work/reports/catreport/reports/{report_uuid}.json")

def make_resistance_report(report_uuid, sample_filepath, sample_name, pipeline_run_uuid):
    '''
    1. symlink sample file path to /work/reports/resistanceapi/vcfs/{report_uuid}.vcf
    2. send request for report to resistance api
    3. write report to /work/reports/catreport/reports/{report_uuid}.json
    4. delete symlink from 1.
    '''
    os.system(f'cd /work/reports/resistanceapi/vcfs; ln -s {sample_filepath} {report_uuid}.vcf')
    url = f'http://localhost:8990/api/v1/resistances/piezo/{report_uuid}?type=piezo'
    logging.warning('res api')
    r = requests.get(url)
    logging.warning('res api end')
    try:
        out_filepath = f'/work/reports/catreport/reports/{report_uuid}.json'
        with open(out_filepath, 'w') as report_file:
            report_file.write(r.text)
        os.system(f'cd /work/reports/resistanceapi/vcfs && rm {report_uuid}.vcf')

    except Exception as e:
        logging.warning("couldn't write report file")
        logging.warning(str(e))

    return out_filepath

def make_trivial_copy_report(report_uuid, sample_filepath, sample_name, pipeline_run_uuid):
    out_filepath = f'/work/reports/catreport/reports/{report_uuid}.json'
    os.system(f'cp {sample_filepath} {out_filepath}')
    return out_filepath

def make_file_copy_report(report_file_path, sample_filepath, sample_name, pipeline_run_uuid):
    out_filepath = f'/work/reports/catreport/reports/{report_file_path}'
    os.system(f'cp {sample_filepath} {out_filepath}')
    return out_filepath

@app.route('/report/<pipeline_run_uuid>/<sample_name>')
def get_report(pipeline_run_uuid, sample_name):
    return json.dumps(getreportlib.get_report(None, con, pipeline_run_uuid, sample_name))

def main():

    threading.Thread(target=report_thread_factory, args=(con, "resistance", make_resistance_report)).start()
    threading.Thread(target=report_thread_factory, args=(con, "mykrobe_speciation", make_trivial_copy_report)).start()
    threading.Thread(target=report_thread_factory, args=(con, "kraken2_speciation", make_trivial_copy_report)).start()
    threading.Thread(target=report_thread_factory, args=(con, "pick_reference", make_trivial_copy_report)).start()
    threading.Thread(target=report_thread_factory, args=(con, "samtools_qc", make_trivial_copy_report)).start()

    threading.Thread(target=report_thread_factory, args=(con, "nfnvm_nanostats_qc", make_trivial_copy_report)).start()
    threading.Thread(target=report_thread_factory, args=(con, "nfnvm_kronareport", make_file_copy_report)).start()
    threading.Thread(target=report_thread_factory, args=(con, "nfnvm_flureport", make_trivial_copy_report)).start()
    threading.Thread(target=report_thread_factory, args=(con, "nfnvm_viralreport", make_trivial_copy_report)).start()
    threading.Thread(target=report_thread_factory, args=(con, "nfnvm_map2coverage_report", make_file_copy_report)).start()

    threading.Thread(target=report_thread_factory, args=(con, "nfnvm_resistance", make_file_copy_report)).start()

    threading.Thread(target=report_thread_factory, args=(con, "run_distmatrix", make_within_run_distreport)).start()

    app.run(port=10000)

if __name__ == '__main__':
    main()
