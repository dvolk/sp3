#
# nfweb is a simple interface to nextflow using the flask web framework
#

import logging
import json
import pathlib
import uuid
import os
import signal
import collections
import base64
import subprocess
import shlex
from io import StringIO
import datetime
import re
import time
import functools
import threading
import contextlib
import ast

import pandas
import requests
from flask import Flask, request, render_template, redirect, abort, url_for, g
import flask_login
from ldap3 import Connection
from passlib.hash import bcrypt

import nflib as nflib
import config as config
import utils as utils
import in_fileformat_helper as in_fileformat_helper

def setup_logging():
    logger = logging.getLogger("ui")
    logger.setLevel(logging.DEBUG)
    c_handler = logging.StreamHandler()
    f_handler = logging.FileHandler("ui.log")
    c_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    f_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(f_handler)
    logger.addHandler(c_handler)
    return logger

logger = setup_logging()
logger.debug("Logging initialized")

app = Flask(__name__)

# This is used for signing browser cookies. Change it in prod. Changing it
# invalidates all current user sessions
app.secret_key = 'secret key'

login_manager = flask_login.LoginManager()
login_manager.init_app(app)
login_manager.login_view = '/login'

@app.errorhandler(404)
def page500(error):
    return render_template('500.template', error=error), 404
@app.errorhandler(403)
def page500(error):
    return render_template('500.template', error=error), 403
@app.errorhandler(500)
def page500(error):
    return render_template('500.template', error=error), 500

def reload_cfg():
    global configFile
    configFile = pathlib.Path("config.yaml")
    global cfg
    cfg = config.Config()
    cfg.load(str(configFile))
    global auth
    auth = cfg.get('authentication')
    global contexts
    contexts = dict()
    for c in cfg.get('contexts'):
        contexts[c['name']] = c
    global flows
    flows = dict()
    for f in cfg.get('nextflows'):
        flows[f['name']] = f
    global users
    users = dict()
    for u in cfg.get('users'):
        users[u['name']] = u
    global ldap
    ldap = dict()
    try:
        for l in cfg.get('ldap'):
            ldap[l['name']] = l
    except Exception as e:
        logger.warning("No LDAP authentication, continuing with builtin")
        logger.warning(e)

reload_cfg()

@app.context_processor
def inject_globals():
    return dict(nfweb_version=cfg.get('nfweb_version'))

# really could just be one function
def api_get_request(api, api_request):
    api_request = "http://{0}:{1}{2}".format(cfg.get(api)['host'],
                                             cfg.get(api)['port'],
                                             api_request)
    logger.debug("api_get_request() => {0}".format(api_request))
    try:
        r = requests.get(api_request)
    except requests.exceptions.ConnectionError as e:
        logger.error("Failed to contact API. Is it running?")
        logger.error(e)
        abort(500, description="Failed to contact API: {0}".format(e))

    logger.debug("api_get_request() <= {0}".format(r.text[:80]))
    try:
        resp = r.json()
    except json.decoder.JSONDecodeError as e:
        logger.error("API returned data that could not be parsed as JSON")
        logger.error(e)
        abort(500, description="Could not parse API response as JSON")
    return resp['data']

def api_post_request(api, api_request, data_json):
    api_request = "http://{0}:{1}{2}".format(cfg.get(api)['host'],
                                             cfg.get(api)['port'],
                                             api_request)
    logger.debug("api_post_request() => {0}".format(api_request))
    try:
        r = requests.post(api_request, json=data_json)
    except requests.exceptions.ConnectionError as e:
        logger.error("Failed to contact API. Is it running?")
        logger.error(e)
        abort(500, description="Failed to contact API: {0}".format(e))

    logger.debug("api_post_request() <= {0}".format(r.text[:80]))
    try:
        resp = r.json()
    except json.decoder.JSONDecodeError as e:
        logger.error("API returned data that could not be parsed as JSON")
        logger.error(e)
        abort(500, description="Could not parse API response as JSON")
    return resp['data']

class User(flask_login.UserMixin):
    pass

@login_manager.user_loader
def user_loader(username):
    if username not in users:
        return
    user = User()
    user.id = username
    return user

@login_manager.request_loader
def request_loader(request):
    username = request.form.get('username')
    if username not in users:
        return
    user = User()
    user.id = username

    form_password = request.form['password']
    password_hash = users[form_username]['password']

    user.is_authenticated = bcrypt.verify(form_password, password_hash)
    return user

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.template')
    if request.method == 'POST':
        form_username = request.form['username']
        form_password = request.form['password']

        if auth == 'ldap':
            '''
            Check user authorization
            '''
            ldap_host = cfg.get('ldap')[0]['host']
            conn = Connection(ldap_host,
                              user=form_username,
                              password=form_password,
                              read_only=True)
            if not conn.bind():
                logger.warning("invalid credentials for ldap user {0}".format(form_username))
                return redirect('/')

            '''
            User is authorized
            '''
            logger.info("ldap user {0} logged in".format(form_username))

            user = User()
            user.id = form_username
            flask_login.login_user(user)

            cap = list()
            if form_username in cfg.get('ldap')[0]['admins']:
                cap = ['admin']

            global users
            users[user.id] = {
                'name': form_username,
                'capabilities' : cap,
            }

            return redirect('/')

        if auth == 'builtin':
            '''
            Check user authorization
            '''
            if not form_username in users:
                logger.warning("unknown user {0}".format(form_username))
                return redirect('/login')

            password_hash = users[form_username]['password']
            if not bcrypt.verify(form_password, password_hash):
                logger.warning("invalid credentials for user {0}".format(form_username))
                return redirect('/login')

            '''
            User is authorized
            '''
            logger.info("user {0} logged in".format(form_username))

            user = User()
            user.id = form_username
            flask_login.login_user(user)

            return redirect('/')
    assert False, "unreachable"

@app.route('/logout')
def logout():
    flask_login.logout_user()
    return redirect('/')

# todo move this and similar to nflib.py
@app.route('/')
@flask_login.login_required
def status():
    response = api_get_request('nfweb_api', '/status')
    running, recent, failed = response['running'], response['recent'], response['failed']
    return render_template('status.template', running=running, recent=recent, failed=failed)

def is_admin():
    return 'admin' in users[flask_login.current_user.id]['capabilities']

@app.route('/userinfo/<username>', methods=['GET', 'POST'])
@flask_login.login_required
def userinfo(username: str):
    is_same = username == flask_login.current_user.id
    username_exists = username in users

    if (not is_same and not is_admin()) or not username_exists:
        return redirect('/')

    return render_template('userinfo.template', userinfo=users[username])

@app.route('/flow/<flow_name>/nf_script')
@flask_login.login_required
def view_nf_script(flow_name):
    response = api_get_request('nfweb_api', '/flow/{0}/nf_script'.format(flow_name))

    if not response or 'nf_script_txt' not in response:
        abort(404, description="Script file not found")

    config_content = response['nf_script_txt']

    return render_template('admin.template', config_yaml=config_content)

@app.route('/edit_flow_config/<flow_name>')
@flask_login.login_required
def edit_flow_config(flow_name):
    response = api_get_request('nfweb_api', '/get_workflow_config_str/{0}'.format(flow_name))

    config_content = response['config_content']

    return render_template('admin.template', config_yaml=config_content)

@app.route('/admin', methods=['GET', 'POST'])
@flask_login.login_required
def admin():
    if not is_admin():
        return redirect('/')

    configFile = pathlib.Path("config.yaml")
    if request.method == 'GET':
        with open(str(configFile)) as f:
            return render_template('admin.template', config_yaml=f.read())

    if request.method == 'POST':
        if request.form['config']:
            old_cfg = cfg.config
            new_cfg = request.form['config']
            try:
                cfg2 = config.Config()
                cfg2.load_str(new_cfg)
            except:
                logger.warning("invalid config string")
                return redirect("/admin")
            try:
                f = open(str(configFile), "w")
                f.write(new_cfg)
            except:
                logger.warning("Couldn't write config.yaml file")
                return redirect("/admin")
            finally:
                f.close()
            try:
                reload_cfg()
            except:
                logger.warning("couldn't reload config")
                cfg.config = old_cfg
                return redirect("/admin")

        return redirect("/admin")

@app.route('/flows')
@flask_login.login_required
def list_flows():
    flows = list()
    for flow in cfg.get('nextflows'):
        flows.append(flow)

    return render_template('list_flows.template', flows=flows)

def get_user_params_dict(flow_name, run_uuid):
    ret = dict()
    response = api_get_request('nfweb_api', '/flow/getrun/{0}'.format(run_uuid))
    run = response["data"]
    if run:
        try:
            data = json.loads(run[0][20])
            if 'user_param_dict' in data:
                ret = data['user_param_dict']
        except json.decoder.JSONDecodeError as e:
            logger.warning("couldn't decode user_param_dict: {0}".format(run[0][20]))
    return ret

def new_run1(flow_name, flow_cfg, form):
    logger.debug('flow_cfg: {0}'.format(flow_cfg))

    run_uuid = str(uuid.uuid4())

    run_name = form['run_name']
    context = form['context']

    reference_map = '{}'
    if 'ref_uuid' in form and form['ref_uuid'] and 'refmap' in flow_cfg:
        logger.debug(f'ref_uuid: \'{form["ref_uuid"]}\'')
        r = api_get_request('nfweb_api', f'/get_reference_cache/{ request.form["ref_uuid"] }')
        reference_map = json.loads(r['reference_json'])
        logger.debug(f'reference_map: {reference_map}')

    current_user = users[flask_login.current_user.id]

    # user parameters, grabbed from run from
    user_param_dict = dict()

    indir = ""
    readpat = ""

    for form_key, form_value in form.items():
        if '-and-' in form_key:
            name, arg = form_key.split('-and-')

            if form_value != "":
                user_param_dict[arg] = form_value

            if name == 'indir':
                indir = form_value
            elif name == 'readpat':
                readpat = form_value

    data = {
        # nfweb run uuid (not to be confused with the uuid generated by nextflow)
        'run_uuid': run_uuid,
        # run name / project name
        'run_name': run_name,
        # execution context (i.e. local or slurm or whatever)
        'context': context,
        # flow config
        'flow_cfg': flow_cfg,
        # individual sample reference map
        'reference_map': reference_map,
        # contexts
        'contexts': contexts,
        # user arguments to nextflow
        'user_param_dict' : user_param_dict,
        # web user id that started the run
        'user_name': flask_login.current_user.id,
        # input directory (if it exists or "" otherwise)
        'indir': indir,
        # filtering regular expression (if it exists or "" otherwise)
        'readpat': readpat
    }

    # convert to json
    logger.debug('data: {0}'.format(data))
    data_json = json.dumps(data)

    response = api_post_request('nfweb_api', '/run/start', data_json)

@app.route('/flow/<flow_name>/new', methods=['GET', 'POST'])
@flask_login.login_required
def begin_run(flow_name: str):
    if flow_name not in flows:
        abort(404, description="Flow not found")

    flow_cfg = flows[flow_name]

    '''
    GET
    '''
    if request.method == 'GET':
        # input directory, grabbed from query string
        fetch_given_input = ''
        # user parameters, grabbed from run from
        user_param_dict = dict()

        subflows = list()
        fetch_given_input_b = ""

        sample_names=list()
        references=list()
        sample_names_references=list()

        guessed_filename_format = ""
        # allow prefilling of the form from the fetch page
        if request.args.get('given_input'):
            fetch_given_input_b = request.args.get('given_input')
            fetch_given_input = base64.b16decode(fetch_given_input_b).decode('utf-8')

            # try to get the sample names and reference
            guessed_filename_format, sample_names = in_fileformat_helper.guess_from_dir(fetch_given_input)
            if sample_names:
                for p in flow_cfg['param']['description']:
                    if p['name'] == 'ref':
                        for k,v in p['options'].items():
                            references.append(v)
        # allow prefilling of the form from other runs
        elif request.args.get('replay'):
            replay_uuid = request.args.get('replay')
            user_param_dict = get_user_params_dict(flow_name, replay_uuid)

        ref_uuid = str()
        if request.args.get('ref_uuid'):
            ref_uuid = request.args.get('ref_uuid')

        logger.debug(sample_names)
        logger.debug(references)
        return render_template('start_run.template',
                               subflows = subflows,
                               ref_uuid=ref_uuid,
                               flow_cfg=flow_cfg,
                               sample_names=sample_names,
                               references=references,
                               given_input=fetch_given_input,
                               fetch_given_input_b=fetch_given_input_b,
                               now=datetime.datetime.now().strftime("%Y%m%d_%H%M%S"),
                               user_param_dict=user_param_dict,
                               guessed_filename_format=guessed_filename_format)

    elif request.method == 'POST':
        logger.debug('form: {0}'.format(request.form))
        new_run1(flow_name, flow_cfg, request.form)
        return redirect("/flow/{0}".format(flow_name))

@app.route('/map_samples', methods=['POST'])
@flask_login.login_required
def map_samples():
    if 'sample_names' in request.form:
        # display table
        return render_template('refmap.template',
                               sample_names=ast.literal_eval(request.form['sample_names']),
                               references=ast.literal_eval(request.form['references']),
                               flow_name=request.form['flow_name'],
                               fetch_given_input_b=request.form['fetch_given_input_b'])
    else:
        # save results in database and redirect to new run
        reference_map = dict()
        for k,v in request.form.items():
            if k[0:5] == '_ref_':
                logger.debug(f'{k}={v}')
                sample_name = k[5:]
                reference = v
                reference_map[sample_name] = reference
        ref_uuid = str(uuid.uuid4())
        data = { 'ref_uuid': ref_uuid,
                 'reference_json': reference_map }
        logger.debug(f'form data: {data}')
        if 'cancel' in request.form:
            return redirect(f'/flow/{ request.form["flow_name"] }/new?given_input={ request.form["fetch_given_input_b"] }')
        else:
            api_post_request('nfweb_api', '/add_to_reference_cache', json.dumps(data))
            return redirect(f'/flow/{ request.form["flow_name"] }/new?given_input={ request.form["fetch_given_input_b"] }&ref_uuid={ ref_uuid }')



@app.route('/flow/<flow_name>')
@flask_login.login_required
def list_runs(flow_name : str):
    if flow_name in flows:
        flow_cfg = flows[flow_name]
    else:
        abort(404, description="Flow not found")

    response = api_get_request('nfweb_api', '/flow/{0}'.format(flow_name))
    data = response["data"]

    subflow_display_names = []
    if 'subflows' in flow_cfg:
        for subflow_name in flow_cfg['subflows']:
            subflow_display_names.append(flows[subflow_name]['display_name'])

    return render_template('list_runs.template',
                           subflow_display_names=subflow_display_names,
                           stuff={ 'display_name': flow_cfg['display_name'],'flow_name': flow_cfg['name'] },
                           data=data)

@app.route('/flow/<flow_name>/go_details/<run_uuid>')
@flask_login.login_required
def go_details(flow_name : str, run_uuid: str):
    # remove flow_name
    response = api_get_request('nfweb_api', '/flow/{0}/go_details/{1}'.format(flow_name, run_uuid))
    content = response['go_details']
    return render_template('show_log.template', content=content, uuid=uuid)


@app.route('/flow/<flow_name>/details/<run_uuid>/task/<sample_name>/<task_name>')
@flask_login.login_required
def run_details_task_nice(flow_name, run_uuid, sample_name, task_name):
    '''
    Get and load the json string containing the ordered trace dict
    '''
    trace_nice = collections.OrderedDict()
    response = api_get_request('nfweb_api', '/trace_nice/{0}'.format(run_uuid))
    if response and 'trace_nice' in response:
        trace_nice = json.loads(response['trace_nice'], object_pairs_hook=collections.OrderedDict)

    task_id_encoded = None
    if sample_name in trace_nice:
        for task in trace_nice[sample_name]:
            if task['nice_name'] == task_name:
                task_id = task['hash']
        task_id_encoded = task_id.replace('/', '-')

    response = api_get_request('nfweb_api', '/flow/getrun/{0}'.format(run_uuid))
    run_name = response['data'][0][19]

    response = api_get_request('nfweb_api', '/task_details/{0}/{1}'.format(run_uuid, task_id_encoded))
    if response and 'task_files' in response and response['task_files']:
        files = response['task_files']
    else:
        abort(404, description="Task not found")

    return render_template('show_task.template',
                           flow_name=flow_name,
                           run_uuid=run_uuid,
                           task_id=task_id,
                           sample_name=sample_name,
                           task_name=task_name,
                           files=files,
                           run_name=run_name,
                           flow_display_name=flows[flow_name]['display_name'])

    return run_details_task(flow_name, run_uuid, task_id_encoded)

@app.route('/flow/<flow_name>/details/<run_uuid>/task/<task_id>')
@flask_login.login_required
def run_details_task(flow_name, run_uuid, task_id):
    if len(task_id) != 9:
        abort(404, description="Task not found")
    response = api_get_request('nfweb_api', '/task_details/{0}/{1}'.format(run_uuid, task_id))
    if response and 'task_files' in response and response['task_files']:
        files = response['task_files']
    else:
        abort(404, description="Task not found")

    response = api_get_request('nfweb_api', '/flow/getrun/{0}'.format(run_uuid))
    run_name = response['data'][0][19]

    return render_template('show_task.template',
                           flow_name=flow_name,
                           run_uuid=run_uuid,
                           task_id=task_id,
                           sample_name="",
                           task_name="",
                           files=files,
                           run_name=run_name,
                           flow_display_name=flows[flow_name]['display_name'])

def get_sample_tags_for_run(run_uuid):
    rows = api_get_request('cattag_api', f'/get_sample_tags_for_run/{run_uuid}')
    ret = collections.defaultdict(list)
    for row in rows:
        ret[row[0]].append([row[1], row[2]])
    print(ret)
    return ret

@app.route('/flow/<flow_name>/details/<run_uuid>')
@flask_login.login_required
def run_details(flow_name : str, run_uuid: int):
    rows = api_get_request('nfweb_api', '/flow/getrun/{0}'.format(run_uuid))

    if not rows or 'data' not in rows or not rows['data'] or not rows['data'][0]:
        abort(404, description="Run not found")

    data = json.loads(rows['data'][0][20])
    user_param_dict = data['user_param_dict']

    '''
    Check if this is a composite run
    '''
    subruns = []
    if 'subflows' in data:
        if 'subflow_uuids' in data:
            for run_uuid_ in data['subflow_uuids']:
                subrun = api_get_request('nfweb_api', '/flow/getrun/{0}'.format(run_uuid_))['data'][0]
                subrun[20] = json.loads(subrun[20])
                subrun_flow_name = subrun[9]
                subrun[20].update({ 'subflow_display_name': flows[subrun_flow_name]['display_name'] })
                subruns.append(subrun)

    logger.debug(subruns)

    response = api_get_request('nfweb_api', '/flow/{0}/details/{1}'.format(flow_name, run_uuid))
    trace, output_dir, buttons, fetch_subdir, run_name = response['trace'], response['output_dir'], response['buttons'], response['fetch_subdir'], response['run_name']

    '''
    Get and load the json string containing the ordered trace dict
    '''
    sample_count = 0
    task_count = 0
    expected_tasks = 0
    trace_nice = collections.OrderedDict()

    response = api_get_request('nfweb_api', '/trace_nice/{0}'.format(run_uuid))

    if response and 'trace_nice' in response:
        trace_nice = json.loads(response['trace_nice'], object_pairs_hook=collections.OrderedDict)

        '''
        Count samples and tasks, subject to certain filters
        '''
        for dataset_id,tasks in trace_nice.items():
            if dataset_id != 'unknown':
                for task in tasks:
                    if task['status'] == 'COMPLETED':
                        if 'count_tasks_ignore' in flows[flow_name]:
                            if task['nice_name'] not in flows[flow_name]['count_tasks_ignore']:
                                task_count += 1
                        else:
                            task_count += 1

        '''
        Get number of input samples and calculate the number of expected tasks (samples * tasks_per_sample)
        '''
        response2 = api_get_request('nfweb_api', '/flow/getrun_counts/{0}'.format(run_uuid))
        if response2 and 'input_files_count' in response2:
            if response2['input_files_count'] > 0:
                if 'count_tasks_per_sample' in flows[flow_name]:
                    expected_tasks = response2['input_files_count'] * flows[flow_name]['count_tasks_per_sample']
                    logger.debug("expected tasks: {0}".format(expected_tasks))

        logger.debug("samples: {0} task count: {1}".format(len(trace_nice), task_count))

    fetch_dir = pathlib.Path(output_dir)
    if fetch_subdir:
        fetch_dir = fetch_dir / fetch_subdir

    fetch_id = base64.b16encode(bytes(str(fetch_dir), encoding='utf-8')).decode('utf-8')

    tags = get_sample_tags_for_run(run_uuid)

    return render_template('run_details.template',
                           uuid=run_uuid,
                           flow_name=flow_name,
                           tags=tags,
                           flow_display_name=flows[flow_name]['display_name'],
                           entries=trace,
                           output_dir=output_dir,
                           buttons=buttons,
                           fetch_id=fetch_id,
                           subruns=subruns,
                           trace_nice=trace_nice,
                           run_name=run_name,
                           user_param_dict=user_param_dict,
                           task_count=task_count,
                           expected_tasks=expected_tasks)

@app.route('/flow/<flow_name>/log/<run_uuid>')
@flask_login.login_required
def show_log(flow_name : str, run_uuid: int):
    response = api_get_request('nfweb_api', '/flow/{0}/log/{1}'.format(flow_name, run_uuid))
    content = response['log']

    return render_template('show_log.template', content=content, flow_name=flow_name, uuid=run_uuid)

@app.route('/flow/<flow_name>/output_files/<run_uuid>')
@flask_login.login_required
def show_output_files(flow_name : str, run_uuid: int):
    response = api_get_request('nfweb_api', '/flow/{0}/output_files/{1}'.format(flow_name, run_uuid))
    try:
        content = response['output_files']
    except:
        content = "Directory inspection commands failed. The directory probably doesn't exist"

    download_url = cfg.get('download_url')

    return render_template('show_files.template', content=content, flow_name=flow_name, uuid=run_uuid,
                           download_url=download_url)

@app.route('/flow/<flow_name>/delete_output_files/<run_uuid>')
def delete_output_files(flow_name, run_uuid):
    api_get_request('nfweb_api', f'/delete_output_files/{run_uuid}')
    return redirect(f"/flow/{flow_name}/details/{run_uuid}")

@app.route('/flow/<flow_name>/delete_run/<run_uuid>')
def delete_run(flow_name, run_uuid):
    api_get_request('nfweb_api', f'/delete_run/{run_uuid}')
    return redirect(f"/flow/{flow_name}")

@app.route('/flow/<flow_name>/report/<run_uuid>')
@flask_login.login_required
def show_report(flow_name : str, run_uuid: int):
    response = api_get_request('nfweb_api', '/flow/{0}/report/{1}'.format(flow_name, run_uuid))
    content = response['report']

    return content

@app.route('/flow/<flow_name>/timeline/<run_uuid>')
@flask_login.login_required
def show_timeline(flow_name: str, run_uuid: int):
    response = api_get_request('nfweb_api', '/flow/{0}/timeline/{1}'.format(flow_name, run_uuid))
    content = response['timeline']

    return content

@app.route('/flow/<flow_name>/dagdot/<run_uuid>')
@flask_login.login_required
def show_dagdot(flow_name: str, run_uuid: int):
    response = api_get_request('nfweb_api', '/flow/{0}/dagdot/{1}'.format(flow_name, run_uuid))
    content = response['dagdot']

    return content

@app.route('/flow/<flow_name>/stop/<run_uuid>')
@flask_login.login_required
def kill_nextflow(flow_name : str, run_uuid: int):
    data = {
        'flow_name': flow_name,
        'run_uuid': run_uuid
    }

    data_json = json.dumps(data)

    response = api_post_request('nfweb_api', '/run/stop', data_json)

    return redirect("/flow/{0}".format(flow_name))

@app.route('/terminate_job/<job_id>')
@flask_login.login_required
def terminate_job(job_id):
    data_json = { 'job_id': job_id }
    response = api_post_request('nfweb_api', '/terminate_job', data_json)
    return redirect('/cluster')

def hm_timediff(epochtime_start, epochtime_end):
    t = epochtime_end - epochtime_start
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    if h > 0:
        return f"{h}h {m}m"
    else:
        return f"{m}m"

@app.route('/cluster')
@flask_login.login_required
def cluster():
    try:
        r = requests.get('http://127.0.0.1:6000/status').json()
        cluster_info = r['nodes']
    except Exception as e:
        about(500, description=e)

    for node_name, node in cluster_info.items():
        for j in node['jobs']:
            for job_id, job in j.items():
                job['duration'] = hm_timediff(job['started'], int(time.time()))

    try:
        df = subprocess.check_output(shlex.split("df -h"), stderr=subprocess.PIPE, universal_newlines=True)
    except FileNotFoundError as e:
        abort(500, description=e)
    except subprocess.CalledProcessError as e:
        abort(500, description=e)

    disk_filter = cfg.get("cluster_view")['disk_filter']
    tbl_df     = pandas.read_csv(StringIO(df), sep='\s+')
    tbl_df = tbl_df[tbl_df.Filesystem.str.contains(disk_filter)][['Mounted', 'Use%', 'Used', 'Size']]

    # embedded content
    embeds = None
    if 'embeds' in cfg.get("cluster_view"):
        embeds = cfg.get("cluster_view")['embeds']

    return render_template('cluster.template', cluster_info=cluster_info, tbl_df=tbl_df, embeds=embeds)

@app.route('/fetch_data')
@flask_login.login_required
def fetch_data():
    r = api_get_request('fetch_api', '/api/fetch/describe')
    sources = r['sources']

    # allow prefilling of the new fetch form
    in_data_kind = None
    in_data_identifier = None

    if 'kind' in request.args and 'id' in request.args:
        in_data_kind = request.args.get('kind')
        in_data_identifier = request.args.get('id')
        in_data_identifier = base64.b16decode(in_data_identifier).decode('utf-8')

    return render_template('new_fetch.template', sources=sources,
                           data_kind=in_data_kind, data_identifier=in_data_identifier)

@app.route('/fetch')
@flask_login.login_required
def fetch():
    r = api_get_request('fetch_api', '/api/fetch/status')
    r2 = api_get_request('fetch_api', '/api/fetch/describe')

    sources = r2['sources']

    # Get the first name of the nextflow and all of them,
    # to allow users to change what to run
    flow_name = cfg.get('nextflows')[0]['name']
    all_flow_names = [x['name'] for x in cfg.get('nextflows')]

    # TODO error checking
    fetches=r

    # change the epoch time in a human-readable format
    # and reformat the output_dir into base 16
    for k,v in fetches.items():
        pretty_started_date = datetime.datetime.fromtimestamp(v['started']).strftime("%F %T")

        output_dir = str(pathlib.Path(sources[v['kind']]['flatten_directory']) / k)
        output_dir_b16 = base64.b16encode(bytes(output_dir, encoding='utf-8')).decode('utf-8')

        v.update({ 'started': pretty_started_date,
                   'output_dir': output_dir_b16
        })

    logger.debug(all_flow_names)
    if request.args.get('flow_name'):
        flow_name = request.args.get('flow_name')
    return render_template('fetch.template', fetches=fetches, flow_name=flow_name,
                           all_flow_names=all_flow_names, sources=sources)

@app.route('/fetch_new')
@flask_login.login_required
def fetch_new():
    fetch_name = request.args.get("fetch_name")
    fetch_range = request.args.get("fetch_range")
    fetch_kind = request.args.get("fetch_kind")

    # base16 encode path to avoid / in url
    fetch_name_b = base64.b16encode(bytes(fetch_name, encoding='utf-8')).decode('utf-8')

    url = '/api/fetch/{0}/new/{1}?fetch_range={2}'.format(fetch_kind, fetch_name_b, fetch_range)
    api_get_request('fetch_api', url)

    return redirect('/fetch')

@app.route('/fetch_delete/<fetch_kind>/<guid>')
@flask_login.login_required
def fetch_delete(fetch_kind, guid):
    api_get_request('fetch_api', "/api/fetch/{0}/delete/{1}".format(fetch_kind, guid))
    return redirect('/fetch')

@app.route('/fetch_stop/<guid>')
@flask_login.login_required
def fetch_stop(guid):
    url = api_get_request('fetch_api', "/api/fetch/stop/{0}".format(guid))
    return redirect('/fetch')

@app.route('/select_flow/<guid>')
@flask_login.login_required
def select_flow(guid):
    ret1 = api_get_request('fetch_api', '/api/fetch/status_sample/{0}'.format(guid))
    flow_name = cfg.get('nextflows')[0]['name']

    if request.args.get('flow_name'):
        flow_name = request.args.get('flow_name')
    if guid in ret1:
        ret1 = ret1[guid]
    else:
        abort(404, description="guid not found")

    if ret1:
        print(ret1)
        accession = ret1['name']
        logger.debug(ret1)
        fetch_range = json.loads(ret1['data'])['fetch_range']
        status = ret1['status']
        progress = ret1['progress']
        total = ret1['total']
        kind = ret1['kind']

        r = api_get_request('fetch_api', '/api/fetch/describe')
        sources = r['sources']

        input_dir = pathlib.Path(sources[kind]['flatten_directory']) / guid

    r2 = api_get_request('fetch_api', '/api/fetch/describe')
    sources = r2['sources']
    output_dir = str(pathlib.Path(sources[ret1['kind']]['flatten_directory']) / guid)
    output_dir_b16 = base64.b16encode(bytes(output_dir, encoding='utf-8')).decode('utf-8')

    # Get the first name of the nextflow and all of them,
    # to allow users to change what to run
    all_flow_names = [x['name'] for x in cfg.get('nextflows')]

    return render_template('select_flow.template',
                           guid=guid,
                           name=accession,
                           fetch_range=fetch_range,
                           status=status,
                           progress=progress,
                           total=total,
                           flow_name=flow_name,
                           all_flow_names = all_flow_names,
                           input_dir=input_dir,
                           output_dir_b16=output_dir_b16)

@app.route('/fetch_details/<guid>')
@flask_login.login_required
def fetch_details(guid):
    ret1 = api_get_request('fetch_api', '/api/fetch/status_sample/{0}'.format(guid))

    if guid in ret1:
        ret1 = ret1[guid]
    else:
        abort(404, description="guid not found")

    ret2 = api_get_request('fetch_api', '/api/fetch/log/{0}'.format(guid))

    if ret1:
        accession = ret1['name']
        logger.debug(ret1)
        fetch_range = json.loads(ret1['data'])['fetch_range']
        status = ret1['status']
        progress = ret1['progress']
        total = ret1['total']
        kind = ret1['kind']

        r = api_get_request('fetch_api', '/api/fetch/describe')
        sources = r['sources']

        input_dir = pathlib.Path(sources[kind]['flatten_directory']) / guid

    file_table = list()
    if ret1:
        if 'ok_files_fastq_ftp' in ret1:
            for i, ok_file in enumerate(ret1['ok_files_fastq_ftp']):
                file_table.append([ok_file, ret1['ok_files_fastq_md5'][i]])

    app_log = ret2['app']

    ena_table = ""
    if 'ena' in ret2 and ret2['ena']:
        logger.debug(ret2['ena'][:80])
        pandas.set_option('display.max_colwidth', -1)
        ena_table = pandas.read_json(ret2['ena']).stack().sort_index().to_frame().to_html()

    return render_template('fetch_details.template',
                           guid=guid,
                           name=accession,
                           fetch_range=fetch_range,
                           status=status,
                           progress=progress,
                           total=total,
                           file_table=file_table,
                           log=app_log,
                           input_dir = input_dir,
                           ena_table=ena_table)

@app.route('/flow/<run_uuid>/<dataset_id>/report')
@flask_login.login_required
def get_report(run_uuid : str, dataset_id: str):
    # TODO add API config
    resp = api_get_request('report_api', f'/report/{run_uuid}/{dataset_id}')

    report_data = resp['report_data'] # data in from catreport
    template_report_data = dict() # data out to template

    if report_data['samtools_qc']:
        template_report_data['samtools_qc'] = dict()
        template_report_data['samtools_qc']['data'] = dict()
        for line in report_data['samtools_qc']['data'].split('\n'):
            elems = line.split('\t')
            if elems[0] == 'SN':
                template_report_data['samtools_qc']['data'][elems[1]] = elems[2]
        template_report_data['samtools_qc']['finished_epochtime'] = time.strftime("%Y/%m/%d %H:%M", time.localtime(report_data['samtools_qc']['finished_epochtime']))

    if report_data['nfnvm_nanostats_qc']:
        template_report_data['nfnvm_nanostats_qc'] = dict()
        template_report_data['nfnvm_nanostats_qc']['data'] = dict()
        for line in report_data['nfnvm_nanostats_qc']['data'].split('\n')[1:8]:
            elems = line.split(':')
            template_report_data['nfnvm_nanostats_qc']['data'][elems[0].strip()] = elems[1].strip()
        template_report_data['nfnvm_nanostats_qc']['finished_epochtime'] = time.strftime("%Y/%m/%d %H:%M", time.localtime(report_data['nfnvm_nanostats_qc']['finished_epochtime']))

    if report_data['nfnvm_kronareport']:
        template_report_data['nfnvm_kronareport'] = dict()
        template_report_data['nfnvm_kronareport']['data'] = report_data['nfnvm_kronareport']['data'] 
        template_report_data['nfnvm_kronareport']['finished_epochtime'] = time.strftime("%Y/%m/%d %H:%M", time.localtime(report_data['nfnvm_kronareport']['finished_epochtime']))

    if report_data['nfnvm_flureport']:
        template_report_data['nfnvm_flureport'] = dict()
        template_report_data['nfnvm_flureport']['data'] = dict()
        [line1, line2, _] = report_data['nfnvm_flureport']['data'].split('\n')
        line1 = line1.split('\t')
        line2 = line2.split('\t')
        for i in range(0, 9):
            template_report_data['nfnvm_flureport']['data'][line1[i]] = line2[i]
        template_report_data['nfnvm_flureport']['finished_epochtime'] = time.strftime("%Y/%m/%d %H:%M", time.localtime(report_data['nfnvm_flureport']['finished_epochtime']))

    if report_data['nfnvm_viralreport']:
        template_report_data['nfnvm_viralreport'] = dict()
        template_report_data['nfnvm_viralreport']['data'] = list()
        for line in report_data['nfnvm_viralreport']['data'].split('\n')[1:]:
            elems = line.split('\t')
            template_report_data['nfnvm_viralreport']['data'].append(elems)
        template_report_data['nfnvm_viralreport']['finished_epochtime'] = time.strftime("%Y/%m/%d %H:%M", time.localtime(report_data['nfnvm_flureport']['finished_epochtime']))

    if report_data['pick_reference']:
        template_report_data['pick_reference'] = dict()
        template_report_data['pick_reference']['data'] = report_data['pick_reference']['data']
        template_report_data['pick_reference']['finished_epochtime'] = time.strftime("%Y/%m/%d %H:%M", time.localtime(report_data['pick_reference']['finished_epochtime']))

    if report_data['resistance']:
        logger.debug(f"*** FROM CATREPORT {report_data['resistance']}")
        # check if it is synonymous mutation (first  amino-acid is same as last amino-acid) or invalid mutation (contain z or Z)
        def is_ok_mutation(eff):
            '''
            Mutations where the mutation does nothing or ends in a z are 'not ok' cf Tim Peto
            '''
            if eff['mutation_name'][0] == eff['mutation_name'][-1] or eff['mutation_name'][-1] in ['z', 'Z']:
                return False
            else:
                return True

        def drug_prediction(effects, drug_name):
            '''
            this returns the resistance prediction for drug

            Although the piezo resistance prediction already includes a prediction, we include
            some extra logic to add the F (failed) prediction.
            '''
            drug_effects = [x for x in effects if drug_name == x['drug_name']]
            '''
            Also, group the effects under drug name
            '''
            # TODO
            template_report_data['resistance']['data'][drug_name] = drug_effects

            '''
            No effects = S
            '''
            if not drug_effects:
                return 'S'

            '''
            All effects are S = S
            '''
            all_S = True
            for eff in drug_effects:
                if eff['prediction'] != 'S':
                    all_S = False
                    break
            if all_S:
                return 'S'

            '''
            At least one R that is an ok mutation = R
            '''
            one_ok_R = False
            for eff in drug_effects:
                if eff['prediction'] == 'R' and is_ok_mutation(eff):
                    one_ok_R = True
                    break
            if one_ok_R:
                return 'R'

            '''
            At least one R that is not an ok mutation = F
            '''
            one_bad_R = False
            for eff in drug_effects:
                if eff['prediction'] == 'R' and not is_ok_mutation(eff):
                    one_bad_R = True
                    break
            if one_bad_R:
                return 'F'

            '''
            No Rs and all U are bad mutations = S
            '''
            all_bad_U = True
            for eff in drug_effects:
                if eff['prediction'] == 'U' and is_ok_mutation(eff):
                    all_bad_U = False
            if all_bad_U:
                return 'S'

            '''
            All other cases = U
            '''
            return 'U'

        template_report_data['resistance'] = dict()
        template_report_data['resistance']['data'] = dict()
        template_report_data['resistance']['data']['resistance_effects'] = collections.defaultdict(list)
        template_report_data['resistance']['data']['res_rev_index'] = collections.defaultdict(list) # gene_mutation -> item

        template_report_data['resistance']['data']['effects'] = report_data['resistance']['data']['effects']
        template_report_data['resistance']['data']['mutations'] = report_data['resistance']['data']['mutations']

        template_report_data['resistance']['data']['prediction_ex'] = dict()
        for drug_name in ['INH', 'RIF', 'PZA', 'EMB', 'AMI', 'KAN', 'LEV', 'STM']:
            template_report_data['resistance']['data']['prediction_ex'][drug_name] = drug_prediction(report_data['resistance']['data']['effects'], drug_name)

        logger.debug(f"prediction_ex: {template_report_data['resistance']['data']['prediction_ex']}")

        for item in report_data['resistance']['data']['effects']:
            if is_ok_mutation(item):
                full_name = item['gene_name'] + '_' + item['mutation_name']
                drug_name = item['drug_name']
                template_report_data['resistance']['data']['resistance_effects'][drug_name].append(item)
                template_report_data['resistance']['data']['res_rev_index'][full_name].append(item)

        logger.debug(f"resistance_effects: {template_report_data['resistance']['data']['resistance_effects']}")
        logger.debug(f"res_rev_index: {template_report_data['resistance']['data']['res_rev_index']}")

        template_report_data['resistance']['finished_epochtime'] = time.strftime("%Y/%m/%d %H:%M", time.localtime(report_data['resistance']['finished_epochtime']))
        logger.debug(f"*** TO TEMPLATE {template_report_data['resistance']}")

    if report_data['mykrobe_speciation']:
        template_report_data['mykrobe_speciation'] = dict()
        template_report_data['mykrobe_speciation']['data'] = report_data['mykrobe_speciation']['data']
        template_report_data['mykrobe_speciation']['finished_epochtime'] = time.strftime("%Y/%m/%d %H:%M", time.localtime(report_data['mykrobe_speciation']['finished_epochtime']))

    if report_data['kraken2_speciation']:
        # read kraken2 tsv
        tbl = pandas.read_csv(StringIO(report_data['kraken2_speciation']['data']),
                              sep='\t', header=None,
                              names=['RootFragments%', 'RootFragments', 'DirectFragments', 'Rank', 'NCBI_Taxonomic_ID', 'Name'])

        # remove leading spaces from name
        tbl['Name'] = tbl['Name'].apply(lambda x: x.strip())
        # get family, genus and species
        template_report_data['kraken2_speciation'] = dict()
        template_report_data['kraken2_speciation']['data'] = dict()
        template_report_data['kraken2_speciation']['data']['family'] = tbl.query('Rank == "F"').head(n=1)
        template_report_data['kraken2_speciation']['data']['genus'] = tbl.query('Rank == "G"').head(n=1)
        template_report_data['kraken2_speciation']['data']['species'] = tbl.query('Rank == "S"').head(n=1)
        template_report_data['kraken2_speciation']['data']['human'] = tbl.query('Name == "Homo sapiens"').head(n=1)
        template_report_data['kraken2_speciation']['data']['mycobacteriaceae'] = tbl.query('Name == "Mycobacteriaceae"').head(n=1)
        # format report time
        template_report_data['kraken2_speciation']['finished_epochtime'] = time.strftime("%Y/%m/%d %H:%M", time.localtime(report_data['kraken2_speciation']['finished_epochtime']))

    return render_template('report.template',
                           pipeline_run_uuid=run_uuid,
                           dataset_id=dataset_id,
                           report=template_report_data)
def main():
    app.run(port=7000)

if __name__ == "__main__":
    main()
