import json
import time
import uuid
import sqlite3
import pathlib
import os
import threading

import requests
import flask
from flask import request, render_template
import yaml

app = flask.Flask(__name__)

def get_instances(persistence_dir):
    ds = list(pathlib.Path(persistence_dir).glob('*'))
    ret = list()
    for d in ds:
        f = open(d / 'instance.yaml').read()
        instance_conf = yaml.load(f)
        updated = time.strftime("%F", time.localtime(int(d.stat().st_mtime)))
        ret.append({ 'dir': d,
                     **instance_conf,
                     'updated': updated })
    return ret

def get_instance(persistence_dir, instance_uuid):
    for instance in get_instances(persistence_dir):
        if instance['id'] == instance_uuid:
            return instance

@app.route('/')
def root():
    labkey_url = 'http://labkey.oxfordfun.com'
    return render_template('main.template',
                           instances=get_instances('/work/persistence'),
                           labkey_url=labkey_url)

@app.route('/cluster_browse/<cluster_id>')
def browse(cluster_id):
    cluster_info = get_instance('/work/persistence', cluster_id)

    con = sqlite3.connect(f'/work/persistence/{cluster_id}/db/catweb.sqlite')
    runs = con.execute('select * from nfruns order by start_epochtime desc').fetchall()
    return render_template('cluster_browse.template',
                           runs=runs,
                           cluster_id=cluster_id,
                           cluster_info=cluster_info)

@app.route('/cluster_run_details/<cluster_id>/<run_uuid>')
def cluster_run_details(cluster_id, run_uuid):
    cluster_info = get_instance('/work/persistence', cluster_id)

    # https://persistent-files.mmmoxford.uk/files/{{ cluster_info['id'] }}/{{ run['run_uuid'] }}">

    output_dir = pathlib.Path('/work') / 'persistence' / cluster_id / 'work' / 'output' / run_uuid
    output_dir_exists = output_dir.is_dir()
    
    con = sqlite3.connect(f'/work/persistence/{cluster_id}/db/catweb.sqlite')
    con.row_factory = sqlite3.Row
    run = con.execute('select * from nfruns where run_uuid = ?', (run_uuid,)).fetchone()
    run_json_data = json.loads(run['data_json'])

    run = dict(run)

    con2 = sqlite3.connect(f'/work/persistence/{cluster_id}/db/catreport.sqlite')
    con2.row_factory = sqlite3.Row
    reports = con2.execute('select * from q where pipeline_run_uuid = ? order by sample_name', (run_uuid,)).fetchall()

    reports = [dict(x) for x in reports]

    for report in reports:
        report['finished_time_str'] = time.strftime("%Y/%m/%d %H:%M",
                                                    time.localtime(int(report['finished_epochtime'])))

    return render_template('cluster_run_details.template',
                           run=run,
                           run_json_data=run_json_data,
                           cluster_info=cluster_info,
                           reports=reports,
                           output_dir_exists=output_dir_exists)

def main():
    app.run(port=11000)

if __name__ == '__main__':
    main()
