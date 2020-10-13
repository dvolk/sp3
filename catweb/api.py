import uuid
import logging
import json
import pathlib
import shlex
import os
import subprocess
import signal
import re
import collections
import threading
import time

from flask import Flask, url_for, jsonify, request, abort
import requests

import nflib
import config
import utils
import db

def setup_logging():
    logger = logging.getLogger("api")
    logger.setLevel(logging.DEBUG)
    c_handler = logging.StreamHandler()
    f_handler = logging.FileHandler("api.log")
    c_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    f_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(f_handler)
    logger.addHandler(c_handler)
    logger.debug("Logging initialized")
    return  logging.getLogger('api')

logger = setup_logging()

app = Flask(__name__)

def make_api_response(status, details=None, data=None):
    return json.dumps({ 'status': status,
                        'details': details,
                        'data': data })

def reload_cfg():
    global configFile
    configFile = pathlib.Path("config.yaml")
    global cfg
    cfg = config.Config()
    cfg.load(str(configFile))
    global contexts
    contexts = dict()
    for c in cfg.get('contexts'):
        contexts[c['name']] = c
    global flows
    flows = dict()
    for f in cfg.get('nextflows'):
        flows[f['name']] = f

reload_cfg()

db.setup_db(cfg.get('db_target'))

@app.route('/add_to_reference_cache', methods=['POST'])
def add_to_reference_cache():
    data = json.loads(request.json)
    db.add_to_reference_cache(data['ref_uuid'], data['reference_json'])
    return make_api_response('success')

@app.route('/get_reference_cache/<ref_uuid>')
def get_reference_cache(ref_uuid):
    return make_api_response('success', data={'reference_json': db.get_reference_cache(ref_uuid) })

@app.route('/run/start', methods = ['POST'])
def start_run():
    # Data to from nfweb.py is passed in here as json
    data = json.loads(request.json)
    logger.debug('Params:', data)

    db.insert_dummy_run(data)

    log_dir = cfg.get('log_dir')
    utils.mkdir_exist_ok(log_dir)
    log_filename = "{0}.log".format(data['run_uuid'])
    log_file =  pathlib.Path(log_dir) / log_filename
    cmd = "( python3 go.py {0} | tee {1} ) &".format(shlex.quote(request.json), log_file)
    logger.debug(cmd)
    os.system(cmd)

    return make_api_response('success')

@app.route('/get_workflow_config_str/<flow_name>')
def get_flow_config_string(flow_name):
    if not flow_name in flows:
        return make_api_response('failure', details={'missing_flow': flow_name})

    if not 'filepath' in flows[flow_name]:
        return make_api_response('failure', details={'missing_flow_filepath': flow_name})

    with open(flows[flow_name]['filepath'], 'r') as f:
        content = f.read()
    return make_api_response('success', data={'config_content': content})

@app.route('/terminate_job', methods=['POST'])
def terminate_job():
    job_id = request.json['job_id']

    requests.get(f'http://127.0.0.1:6000/terminate/{ job_id }')
    return make_api_response('success')

@app.route('/run/stop', methods = ['POST'])
def stop_run():
    # Data to from nfweb.py is passed in here as json
    data = json.loads(request.json)
    flow_name = data['flow_name']
    run_uuid = data['run_uuid']

    data = db.get_run(run_uuid)
    nf_directory = pathlib.Path(data[0][11])

    # Using root_dir
    pid_filename = nf_directory / 'runs' / run_uuid / '.run.pid'
    logger.info(f'pid filename {pid_filename}')

    if pid_filename.exists():
        with open(str(pid_filename)) as f:
            pid = int(f.readline())
        os.kill(pid, signal.SIGTERM)
    else:
        logger.error(f'pid filename {pid_filename} doesnt exist')

    return make_api_response('success')

cmds = list()

def once_cmd_async(cmd):
    '''
    run a system command in a thread, but only once
    '''
    if cmd not in cmds:
        logger.warning(f'once_cmd_async: {cmd}')
        def f(cmd):
            os.system(cmd)

        cmds.append(cmd)
        threading.Thread(target=f, args=(cmd,)).start()

    return True

@app.route('/delete_output_files/<run_uuid>')
def delete_output_files(run_uuid):
    try:
        uuid.UUID(run_uuid)
        once_cmd_async(f'rm -rf /work/output/{run_uuid}')
    except Exception as e:
        logger.error(e)
        return make_api_response('failure', details=str(e))
    return make_api_response('success')

@app.route('/delete_run/<run_uuid>')
def delete_run(run_uuid):
    try:
        uuid.UUID(run_uuid)
        db.delete_run(run_uuid)
        once_cmd_async(f'rm -rf /work/runs/{run_uuid}')
        once_cmd_async(f'rm -rf /work/output/{run_uuid}')
    except Exception as e:
        logger.error(e)
        return make_api_response('failure', details=str(e))
    return make_api_response('success')

@app.route('/status/<org>/<is_admin>', methods = ['GET'])
def get_status(org, is_admin, db=db):
    running, recent, failed = db.get_status(org, is_admin)
    return make_api_response('success', data={'running': running,
                                              'recent': recent,
                                              'failed': failed})

@app.route('/flow/<flow_name>', methods = ['GET'])
def get_workflow(flow_name):
    data = db.get_workflow(flow_name)
    data = [list(datum) for datum in data]

    for datum in data:
        uuid = datum[14]
        input_files_count, output_files_count = db.get_input_files_count(uuid)
        datum.append(input_files_count)
        datum.append(str(output_files_count))

    return make_api_response('success', data={'data': data})

@app.route('/flow/getrun_counts/<run_uuid>')
def getrun_counts(run_uuid):
    input_files_count, output_files_count = db.get_input_files_count(run_uuid)
    return make_api_response('success', data={'input_files_count': input_files_count,
                                              'output_files_count': output_files_count })


@app.route('/flow/getrun/<run_uuid>', methods = ['GET'])
def get_run(run_uuid):
    data = db.get_run(run_uuid)
    return make_api_response('success', data={'data': data})

@app.route('/flow/<flow_name>/go_details/<run_uuid>', methods = ['GET'])
def get_go_details(flow_name, run_uuid):
    log_dir = cfg.get('log_dir')
    log_filename =  pathlib.Path(log_dir) / "{0}.log".format(run_uuid)

    with open(str(log_filename)) as lf:
        content = lf.read()

    return make_api_response('success', data={'go_details': content})

@app.route('/flow/<flow_name>/nf_script')
def flow_nf_script(flow_name):
    '''
    Return nextflow script for flow
    '''

    '''
    This shouldn't happen because the config would fail validation with this key
    But let's check anyway in case the validation was ignored...
    '''
    if 'canonical_prog_dir' not in cfg.config:
        return make_api_response('failure', details={'missing_config_key': 'canonical_prog_dir'})

    prog_dir = pathlib.Path(cfg.get('canonical_prog_dir'))

    nf_script_filename = prog_dir / flows[flow_name]['prog_dir'] / flows[flow_name]['script']

    logger.debug("nf_script_filename: {0}".format(nf_script_filename))

    if not nf_script_filename.is_file():
        return make_api_response('failure', details={'missing_nf_script': str(nf_script_filename)})

    with open(str(nf_script_filename)) as f:
        nf_script_txt = f.read()

    return make_api_response('success', data={'nf_script_filename': str(nf_script_filename),
                                              'nf_script_txt': nf_script_txt })


@app.route('/trace_nice/<run_uuid>')
def trace_nice(run_uuid):
    data = db.get_run(run_uuid)

    nf_directory = pathlib.Path(data[0][11])

    trace_filename = nf_directory / 'runs' / run_uuid / 'trace.txt'
    logger.debug("trace filename: {0}".format(str(trace_filename)))

    trace = []
    if trace_filename.is_file():
        trace = nflib.parse_trace_file(trace_filename)

    '''
    dict from sample/nextflow tag to list of trace entries with that sample

    trace entries that couldn't be parsed go into the "unknown" key
    '''
    trace_nice = collections.OrderedDict()
    trace_nice['unknown'] = []

    '''
    Construct trace_nice
    '''
    for entry in trace:
        m = re.search('(.*) \((.*)\)', entry['name'])
        if not m:
            trace_nice['unknown'].append(entry)
            continue
        task_name = m.group(1)
        dataset_id = m.group(2)
        entry['nice_name'] = task_name
        entry['dataset_id'] = dataset_id
        if dataset_id in trace_nice:
            trace_nice[dataset_id].append(entry)
        else:
            trace_nice[dataset_id] = [entry]

    return make_api_response('success', data={'trace_nice': json.dumps(trace_nice)})

@app.route('/task_details/<run_uuid>/<task_id>')
def task_details(run_uuid, task_id):
    '''
    return the .command.* files in the nextflow task directory
    '''

    data = db.get_run(run_uuid)
    nf_directory = pathlib.Path(data[0][11])

    work_dir = nf_directory / 'runs' / run_uuid / 'work'
    if not work_dir.is_dir():
        return make_api_response('failure', details={'missing_task_id': task_id, 'work_dir': str(work_dir)})

    logger.debug(work_dir)

    truncated_task_subdir = task_id.replace('-','/')
    full_task_subdir = list(work_dir.glob(truncated_task_subdir + '*'))
    if not full_task_subdir:
        return make_api_response('failure', details={'missing_task_id': task_id, 'work_dir': str(work_dir)})

    full_task_subdir = full_task_subdir[0]

    if not full_task_subdir.is_dir():
        return make_api_response('failure', details={'missing_task_id': task_id, 'work_dir': str(work_dir)})

    '''
    dictionary of { filename: file contents }
    '''
    file_contents = {}
    for filename in full_task_subdir.glob('*'):
        if filename.is_file() and '.command.' in str(filename):
            with open(str(filename), 'r') as f:
                file_contents[str(filename.name)] = f.read()

    return make_api_response('success', data={'task_files': file_contents})

@app.route('/flow/<flow_name>/details/<run_uuid>', methods = ['GET'])
def get_details(flow_name, run_uuid):
    logger.debug("flow_name: {0}, run_uuid: {1}".format(flow_name, run_uuid))
    data = db.get_run(run_uuid)

    # root_dir is entry 11
    nf_directory = pathlib.Path(data[0][11])
    output_dir = pathlib.Path(data[0][13])
    input_dir = pathlib.Path(json.loads(data[0][20])['indir'])
    run_name = data[0][19]

    buttons = {}

    if output_dir.is_dir():
        buttons['output_files'] = True
        buttons['fetch'] = True

    if input_dir.is_dir():
        buttons['rerun'] = True

    pid_filename = nf_directory / 'runs' / run_uuid / '.run.pid'
    if pid_filename.is_file():
        buttons['stop'] = True

    log_filename = nf_directory / 'runs' / run_uuid / '.nextflow.log'
    if log_filename.is_file():
        buttons['log'] = True

    report_filename = nf_directory / 'runs' / run_uuid / 'report.html'
    if report_filename.is_file():
        buttons['report'] = True

    timeline_filename = nf_directory / 'runs' / run_uuid / 'timeline.html'
    if timeline_filename.is_file():
        buttons['timeline'] = True


    trace_filename = nf_directory / 'runs' / run_uuid / 'trace.txt'
    logger.debug("trace filename: {0}".format(str(trace_filename)))

    trace_nt = None
    if trace_filename.is_file():
        trace_nt = nflib.parse_trace_file(trace_filename)

    fetch_subdir = None
    if 'output' in flows[flow_name] and 'fetch_subdir' in flows[flow_name]['output']:
        fetch_subdir = flows[flow_name]['output']['fetch_subdir']

    return make_api_response('success', data={'trace': trace_nt,
                                              'output_dir': str(output_dir),
                                              'buttons': buttons,
                                              'fetch_subdir': fetch_subdir,
                                              'run_name': run_name })

@app.route('/flow/<flow_name>/log/<run_uuid>', methods = ['GET'])
def get_log(flow_name, run_uuid):
    data = db.get_run(run_uuid)

    nf_directory = pathlib.Path(data[0][11])

    # Using root_dir
    log_filename =  nf_directory / 'runs' / run_uuid / '.nextflow.log'
    content = None
    with open(str(log_filename)) as f:
        content = f.read()

    return make_api_response('success', data={'log': content})

@app.route('/flow/<flow_name>/output_files/<run_uuid>', methods = ['GET'])
def get_output_files(flow_name, run_uuid):
    data = db.get_run(run_uuid)
    # Using root_dir
    output_dir = data[0][13]

    du_cmd = ["du", "-sh", output_dir]
    tree_cmd = ["tree", output_dir]

    logger.debug("du command: {0}".format(du_cmd))
    try:
        du_p = subprocess.check_output(du_cmd, stderr=subprocess.PIPE, universal_newlines=True)
    except subprocess.CalledProcessError:
        return make_api_response('failure', details={'command_failed': 'du'})

    logger.debug("tree command: {0}".format(tree_cmd))
    try:
        result = dict()
        def try_tree(result):
            result['result'] = subprocess.check_output(tree_cmd, stderr=subprocess.PIPE, universal_newlines=True)
        t = threading.Thread(target=try_tree, args=(result,))
        t.start()
        t.join(timeout=3)
        tree_p = result['result']
    except KeyError:
        tree_p = "\n\ntree command failed with timeout\n\n"

    # Format directory on top, then total size, then the file tree
    size_str = du_p.strip()
    size_str = size_str.split("\t")
    size_str = "Total size: {0}".format(size_str[0])
    out_str = tree_p.strip().split('\n')
    out_str = "\n".join([out_str[0].strip()] + [out_str[-1]] + [size_str] + [""] + out_str[1:-1])

    return make_api_response('success', data={'output_files': out_str})

@app.route('/flow/<flow_name>/report/<run_uuid>', methods = ['GET'])
def get_report(flow_name, run_uuid):
    data = db.get_run(run_uuid)

    nf_directory = pathlib.Path(data[0][11])

    report_filename = nf_directory / 'runs' / run_uuid / 'report.html'
    with open(str(report_filename)) as f:
        content = f.read()

    return make_api_response('success', data={'report': content})

@app.route('/flow/<flow_name>/timeline/<run_uuid>', methods = ['GET'])
def get_timeline(flow_name, run_uuid):
    data = db.get_run(run_uuid)

    nf_directory = pathlib.Path(data[0][11])

    timeline_filename = nf_directory / 'runs' / run_uuid / 'timeline.html'
    with open(str(timeline_filename)) as f:
        content = f.read()

    return make_api_response('success', data={'timeline': content})

@app.route('/flow/<flow_name>/dagdot/<run_uuid>', methods = ['GET'])
def get_dagdot(flow_name, run_uuid):
    data = db.get_run(run_uuid)

    nf_directory = pathlib.Path(data[0][11])

    dagdot_filename = nf_directory / 'runs' / runs_uuid / 'dag.dot'

    with open(str(dagdot_filename)) as f:
        content = f.read()

    return make_api_response('success', data={'log': content})

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=7100)
