'''
Fetch API endpoints

/api/fetch/stop
/api/fetch/status
/api/fetch/status_single
/api/fetch/log

/api/fetch/ena/new
/api/fetch/ena/delete
'''

import logging
import uuid
import json
import pathlib
import base64

from flask import Flask, abort, request

import util
import sqlitequeue
from config import config

queue = sqlitequeue.SqliteQueue(config.get('queue_sqlite_target'))

import ena1.api
import ena1.fetcher
import ena1.flatten

import local1.api
import local1.fetcher
import local1.flatten

def setup_logging():
    '''
    setup global logger
    '''
    glogger = logging.getLogger("fetch_logger")
    glogger.setLevel(logging.DEBUG)
    c_handler = logging.StreamHandler()
    c_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    glogger.addHandler(c_handler)

app = Flask(__name__)

@app.route('/api/fetch/stop/<string:in_guid>')
def stop(in_guid):
    glogger = logging.getLogger('fetch_logger')
    if queue.get_val(in_guid, "status") not in ["queued", "running"]:
        return json.dumps(util.make_api_response('success'), data={'state': 'not in valid configuration'})

    def mark_stop(s):
        j = json.loads(s)
        j['stop'] = True
        return json.dumps(j)

    r = queue.apply_fun(in_guid, 'data', mark_stop)
    return json.dumps(util.make_api_response('success'))

@app.route('/api/fetch/status/')
def fetch_status():
    return json.dumps(util.make_api_response('success', data=queue.tolist()))

@app.route('/api/fetch/status_sample/<string:in_guid>')
def fetch_status_sample(in_guid):
    return json.dumps(util.make_api_response('success', data=queue.tolist(in_guid)))

#
# TODO should this be per-kind?
#
@app.route('/api/fetch/log/<string:in_guid>')
def fetch_log(in_guid):
    glogger = logging.getLogger('fetch_logger')
    in_guid = str(pathlib.Path(in_guid).name) # anti-hacker protection

    ret1 = ""
    try:
        with open('logs/{0}.log'.format(in_guid)) as log:
            ret1 = log.read()
    except:
        abort(404)
    ret2 = ""
    try:
        with open('logs/{0}.ena.log'.format(in_guid)) as log:
            ret2 = log.read()
    except:
        pass
    return json.dumps(util.make_api_response('success', data={'app': ret1, 'ena': ret2 }))

@app.route('/api/fetch/describe')
def describe():
    sources = { 
        'ena1': 
        { 
            'description': 'fetch paired fastq reads from ENA (data identifier: accession)',
            'flatten_directory': config.get('ena_flatten_dir')
        },
        'local1': 
        {
            'description': 'fetch from local filesystem (data identifier: local directory)',
            'flatten_directory': config.get('local_flatten_dir')
        }
    }
    return json.dumps(util.make_api_response('success', data= { 'sources': sources }))

@app.route('/api/fetch/ena1/new/<in_accession_b>')
def ena1_new(in_accession_b):
    in_accession = base64.b16decode(in_accession_b).decode('utf-8')

    return ena1.api.ena_new(in_accession, request.args)

@app.route('/api/fetch/ena1/delete/<in_guid>')
def ena1_delete(in_guid):
    return ena1.api.ena_delete(in_guid)

@app.route('/api/fetch/local1/new/<in_accession_b>')
def local1_new(in_accession_b):
    in_accession = base64.b16decode(in_accession_b).decode('utf-8')

    return local1.api.local1_new(in_accession, request.args)

@app.route('/api/fetch/local1/delete/<in_guid>')
def local1_delete(in_guid):
    return local1.api.local1_delete(in_guid)

def main():
    setup_logging()

    glogger = logging.getLogger('fetch_logger')
    glogger.info("starting")

    ena1.api.ena1_api_start()
    local1.api.local1_api_start()

    app.run(host='127.0.0.1', port=7200, debug=False)

if __name__ == '__main__':
    main()
