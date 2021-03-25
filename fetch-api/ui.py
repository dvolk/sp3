import json
import logging
import threading
import time
import hashlib
from ftplib import FTP
from io import StringIO
import uuid
import pathlib
import waitress

import requests
import pandas
from flask import Flask, render_template, abort

from config import config

app = Flask(__name__)

@app.route('/ui/')
def ui():
    try:
        r = requests.get('http://127.0.0.1:5001/api/fetch/status')
    except:
        return "failed to contact api"
    ret = json.loads(r.text)
    data = ret['data']

    fetch_table = list()
    for guid, tbl in data.items():
        name = tbl['name']
        t = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(int(tbl['started'])))
        progress = tbl['progress']
        total = tbl['total']
        fetch_table.append([t, tbl['kind'], guid, tbl['name'], tbl['status'], progress, total])

    return render_template('main.html', fetch_table=fetch_table)

@app.route('/ui/details/<guid>')
def details(guid):
    try:
        r1 = requests.get('http://127.0.0.1:5001/api/fetch/status_sample/{0}'.format(guid))
    except:
        return "failed to contact api"
    ret1 = json.loads(r1.text)
    if guid in ret1['data']:
        ret1 = ret1['data'][guid]
    else:
        ret1 = None
    try:
        r2 = requests.get('http://127.0.0.1:5001/api/fetch/log/{0}'.format(guid))
    except:
        return "failed to contact api"
    if ret1:
        data = json.loads(ret1['data'])
        accession = ret1['name']
        fetch_range = data['fetch_range']
        status = ret1['status']
        progress = ret1['progress']
        total = ret1['total']
        input_dir = pathlib.Path(config.get('ena_flatten_dir')) / guid

    file_table = list()
    if ret1:
        if 'ok_files_fastq_ftp' in data:
            for i, ok_file in enumerate(data['ok_files_fastq_ftp']):
                file_table.append([ok_file, data['ok_files_fastq_md5'][i]])

    try:
        ret2 = json.loads(r2.text)
    except:
        pass

    app_log = ret2['data']['app']

    pandas.set_option('display.max_colwidth', -1)
    ena_table = pandas.read_json(ret2['data']['ena']).stack().to_frame().to_html()

    return render_template('ena_detail.html', guid=guid, name=accession,
                           fetch_range=fetch_range, status=status, progress=progress, 
                           input_dir=input_dir,file_table=file_table, total=total,
                           log=app_log, ena_table=ena_table)

@app.route('/ui/showlog/<guid>')
def log(guid):
    r = requests.get('http://127.0.0.1:5001/api/fetch/log/{0}'.format(guid))
    return "<pre>{0}</pre>".format(json.loads(r.text)['data']['app3'])

waitress.serve(app, listen="127.0.0.1:5002")
