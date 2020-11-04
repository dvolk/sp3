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
import datetime

import requests
from flask import Flask, abort, request

import util
import sqlitequeue
from config import config

queue = sqlitequeue.SqliteQueue(config.get('queue_sqlite_target'))

import ena1.api
import ena1.fetcher
import ena1.flatten

import ena2.api
import ena2.fetcher
import ena2.flatten

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
        return json.dumps(util.make_api_response('success', data={'state': 'not in valid configuration'}))
    t = queue.get_val(in_guid, "kind")

    if t == 'ena1':
        ena1.api.stop_download()

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

    ret1 = "No log found"
    try:
        with open('logs/{0}.log'.format(in_guid)) as log:
            ret1 = log.read()
    except:
        pass

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
        'ena2':
        {
            'display_name': 'ENA - list of sample accessions',
            'description': 'Fetch paired fastq SRA reads from the ENA.',
            'data_identifier_display_name': 'Accession',
            'data_filter_display_name': 'Filter',
            'flatten_directory': config.get('ena_flatten_dir'),
            'has_data_filter': 'no',
            'fetch_methods': None
        },
        'ena1':
        {
            'display_name': 'ENA - one project or accession',
            'description': 'Fetch paired fastq SRA reads from the ENA.',
            'data_identifier_display_name': 'Accession',
            'data_filter_display_name': 'Filter',
            'flatten_directory': config.get('ena_flatten_dir'),
            'has_data_filter': 'yes',
            'fetch_methods': None
        },
        'local1':
        {
            'display_name': 'Local server',
            'description': '''Fetch from local filesystem.
                              Pick this if you're using SFTP or S3''',
            'data_identifier_display_name': 'Local path',
            'flatten_directory': config.get('local_flatten_dir'),
            'local_glob_directories': config.get('local_glob_directories'),
            'has_data_filter': 'no',
            'fetch_methods': ['link', 'copy']
        }
    }
    return json.dumps(util.make_api_response('success', data= { 'sources': sources }))

@app.route('/api/fetch/<fetch_kind>/new', methods=['POST'])
def fetch_new(fetch_kind):
    data = request.json
    fetch_name = data['fetch_name']

    if fetch_kind == 'ena1':
        ret = ena1.api.ena_new(fetch_name, data)
        return ret

    if fetch_kind == 'ena2':
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        fetch_name = fetch_name + '_' + timestamp
        fetch_samples  = data['fetch_samples']

        rows  = fetch_samples.split('\r\n')
        samples = [x.strip() for x in rows if ('ERR' in x or 'SRR' in x)]

        data['fetch_name'] = fetch_name
        data['fetch_samples'] = samples

        ret = ena2.api.ena2_new(fetch_name, data)
        return ret

    if fetch_kind == 'local1':
        ret = local1.api.local1_new(fetch_name, data)
        try_register_sp3data(ret, fetch_name)
        return ret

@app.route('/api/fetch/ena1/delete/<in_guid>')
def ena1_delete(in_guid):
    return ena1.api.ena_delete(in_guid)

@app.route('/api/fetch/ena2/delete/<in_guid>')
def ena2_delete(in_guid):
    return ena2.api.ena_delete(in_guid)

def try_register_sp3data(args, in_accession):
    guid = json.loads(args)['data']['guid']
    directory = in_accession

    try:
        # attempt to register the dataset with catpile api
        requests.post("http://127.0.0.1:22000/load_sp3_data",
                      headers = {'content-type': 'application/json'},
                      data = json.dumps({ "fetch_uuid": guid,
                                          "fetch_dir": directory }))
    except Exception as e:
        glogger = logging.getLogger('fetch_logger')
        glogger.warning("catpile error: {str(e)}")

@app.route('/api/fetch/local1/delete/<in_guid>')
def local1_delete(in_guid):
    return local1.api.local1_delete(in_guid)

def main():
    setup_logging()

    pathlib.Path('logs').mkdir(exist_ok=True)

    glogger = logging.getLogger('fetch_logger')
    glogger.info("starting")

    ena1.api.ena1_api_start()
    ena2.api.ena2_api_start()
    local1.api.local1_api_start()

    app.run(host='127.0.0.1', port=7200, debug=False)

if __name__ == '__main__':
    main()
