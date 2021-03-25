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
import functools
import waitress

import resistance_help
import getreportlib

with open('catreport.yaml') as f:
    config = yaml.load(f.read())

app = flask.Flask(__name__)

con = sqlite3.connect(config['db_target'], check_same_thread=False)
con.execute('create table if not exists q (uuid primary key, type, status, added_epochtime, started_epochtime, finished_epochtime, pipeline_run_uuid, sample_name, sample_filepath, report_filename, software_versions)')
con.execute('create index if not exists q_pipeline_uuids on q (pipeline_run_uuid)')
con.execute('create index if not exists q_type on q (type)')
con.execute('create index if not exists q_status on q (status)')

sql_lock = threading.Lock()

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

def get_report_for_type(pipeline_run_uuid, sample_name, report_type):
    '''
    Query database for report

    Mandatory inputs: pipeline run uuid, sample name, report type
    '''
    return db_get_report_for_type(con, pipeline_run_uuid, sample_name, report_type)

@app.route('/report/<pipeline_run_uuid>/<sample_name>')
def get_report(pipeline_run_uuid, sample_name):
    return json.dumps(getreportlib.get_report(None, con, sql_lock, pipeline_run_uuid, sample_name))

def main():
    waitress.serve(app, listen='127.0.0.1:10001')

if __name__ == '__main__':
    main()
