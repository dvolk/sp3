#
# nfweb is a simple interface to nextflow using the flask web framework
#

import logging
import json
import pathlib
import uuid
import os
import collections
import base64
import subprocess
import shlex
from io import StringIO
import datetime
import time
import ast
import sys
import glob
import csv

import pandas
import requests
from flask import Flask, request, render_template, redirect, abort, url_for, g, make_response
import flask_login
from passlib.hash import bcrypt
from werkzeug.utils import secure_filename
from werkzeug.urls import url_parse

import authenticate
import nflib
import config
import utils
import in_fileformat_helper

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
    global contexts
    contexts = dict()
    for c in cfg.get('contexts'):
        contexts[c['name']] = c
    global flows
    flows = dict()
    for f in cfg.get('nextflows'):
        flows[f['name']] = f
    global auth_builtin
    auth_builtin = dict()
    try:
        auth_builtin = cfg.get('auth_builtin')
    except KeyError:
        pass
    global users
    users = dict()

reload_cfg()

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

    token = users[username]['token']
    attribs = authenticate.attributes_from_user_token(token)
    if not attribs:
        return
    if 'catweb_user' not in attribs:
        return
    if 'requires_review' in attribs:
        return

    org_name = attribs['catweb_organisation']
    org_data = authenticate.get_organisation(org_name)

    user = User()
    user.id = username
    users[user.id]['attributes'] = attribs
    users['org_name'] = org_name
    users['org_data'] = org_data
    return user

def is_admin():
    try:
        return 'catweb_admin' in users[flask_login.current_user.id]['attributes']
    except:
        return False

@app.context_processor
def inject_globals():
    return { 'catweb_version': cfg.get('catweb_version'),
             'is_admin': is_admin() }

@app.route('/register_sp3_user', methods=["GET", "POST"])
def register_sp3_user():
    if request.method == "GET":
        return render_template('register.template')
    if request.method == "POST":
        name = request.form['name']
        job_title = request.form['job_title']
        job_address = request.form['job_address']
        referal = request.form['referal']
        country = request.form['country']
        email = request.form['email']
        username = request.form['username']
        password = request.form['password']
        organisation = request.form['organisation']

        requests.get("http://localhost:13666/add_user", params = request.form)
        return redirect("/")

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        msg = request.args.get('m')

        msgs = { 'wrong_login': 'Supplied login credentials are incorrect.',
                 'not_active': 'User account has not been activated. Please contact the administrators after 1 day.',
                 'no_org': 'User is not in any organisation. Please contact the administrators.',
                 'wrong_org': 'User belongs to organisation with invalid configuration. Please contact the administrators.' }

        return render_template('login.template',
                               next=request.args.get('next'),
                               msgs=msgs,
                               msg=msg)
    if request.method == 'POST':
        if not 'username' in request.form or not 'password' in request.form:
            logging.warning(f"form submitted without username or password")
            return redirect('/')

        form_username = request.form['username']
        form_password = request.form['password']

        token = authenticate.check_authentication(form_username, form_password)

        if token:
            logger.warning(f"user {form_username} verified")
        else:
            logger.warning(f"invalid credentials for user {form_username}")
            return redirect(url_for('login', m='wrong_login'))

        attribs = authenticate.attributes_from_user_token(token)

        if 'requires_review' in attribs:
            return redirect(url_for('login', m='not_active'))

        # organisation stuff
        org_name = attribs['catweb_organisation']
        org_data = authenticate.get_organisation(org_name)

        if not org_data:
            return redirect(url_for('login', m='no_org'))
        if not 'upload_dirs' in org_data:
            return redirect(url_for('login', m='wrong_org'))
        if not 'pipelines' in org_data:
            return redirect(url_for('login', m='wrong_org'))

        upload_dirs = org_data['upload_dirs']
        user_upload_dir = pathlib.Path(f'/data/inputs/users/{ form_username }')
        if not user_upload_dir.exists():
            user_upload_dir.mkdir()

        upload_dirs.append(str(user_upload_dir))


        '''
        User is authorized
        '''
        user = User()
        user.id = form_username
        flask_login.login_user(user)

        users[user.id] = {
            'name': form_username,
            'org_name': org_name,
            'org_data': org_data,
            'token': token,
            'upload_dirs': upload_dirs,
            'attributes': attribs
        }

        logger.warning(f"{form_username} - {users[user.id]}")

        next = request.form.get('next')
        logger.warning(f"next url: {next}")

        if not next or next == "/None" or next == "None" or url_parse(next).netloc != '':
            next = '/'

        return redirect(next)

    assert False, "unreachable"

@app.route('/password' , methods=['GET', 'POST'])
@flask_login.login_required
def change_pw():
    username = flask_login.current_user.id
    logger.debug(f'username: {username}')
    token = users[username]["token"]

    if request.method == 'GET':
        logger.debug(f'username: {username}')
        return render_template('password.template',
        username = username)
    else:
        form_password1 = request.form['password1']
        form_password2 = request.form['password2']

        if form_password1 == form_password2:
            res = requests.get(f'http://localhost:13666/change_password/{token}', params={'new_password':form_password1})
            logger.debug(f'Call catdap changing password for {username}: {res}')
            if res.text == 'OK':
                return redirect('/')
            else:
                return redirect('/password')
        else:
            return redirect('/')

@app.route('/logout')
def logout():
    flask_login.logout_user()
    return redirect('/')

def get_user_pipelines(username):
    ret = list()
    if is_admin():
        return flows.keys()
    else:
        return get_user_dict()['org_data']['pipelines']

# todo move this and similar to nflib.py
@app.route('/')
@flask_login.login_required
def status():
    if 'org_name' in get_user_dict():
        org = get_user_dict()['org_name']
    else:
        org = 'None'

    response = api_get_request('nfweb_api', f'/status/{org}/{str(is_admin())}')
    logging.error("recent: {response['recent']}")
    running, recent, failed = response['running'], response['recent'], response['failed']

    return render_template('status.template', running=running, recent=recent, failed=failed,
                           user_pipeline_list=get_user_pipelines(flask_login.current_user.id))

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

    return render_template('view_nf_script.template', config_yaml=config_content)

@app.route('/edit_flow_config/<flow_name>')
@flask_login.login_required
def edit_flow_config(flow_name):
    response = api_get_request('nfweb_api', '/get_workflow_config_str/{0}'.format(flow_name))

    config_content = response['config_content']

    return render_template('view_flow_config.template', config_yaml=config_content)

@app.route('/admin_edit_user', methods=['GET', 'POST'])
@flask_login.login_required
def admin_edit_user():
    if not is_admin():
        return redirect('/')

    username = request.args['username']

    if request.method == 'GET':
        user_data = json.dumps(requests.get('http://localhost:13666/get_user',
                                            params={ 'username': username }).json(),
                               indent=4)
        return render_template('admin_edit_user.template',
                               username=username,
                               user_data=user_data)

    if request.method == 'POST':
        requests.get("http://localhost:13666/edit_user",
                     params={ 'username': username,
                              'user_data': request.form['user_data'] })

        return redirect(f'/admin_edit_user?username={username}')

@app.template_filter('epochtodate')
def epochtodate(value):
    t = time.localtime(int(value))
    return f"{t.tm_mday}-{t.tm_mon}-{t.tm_year}"

@app.route('/admin')
@flask_login.login_required
def admin():
    if not is_admin():
        return redirect('/')

    with open('config.yaml') as f:
        user_d = requests.get("http://localhost:13666/get_users").json()
        return render_template('admin.template',
                               config_yaml=f.read(),
                               user_d=user_d)

@app.route('/flows')
@flask_login.login_required
def list_flows():
    flows = list()
    for flow in cfg.get('nextflows'):
        flows.append(flow)

    return render_template('list_flows.template', flows=flows,
                           user_pipeline_list=get_user_pipelines(flask_login.current_user.id))

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
    fetch_uuid = form['fetch_uuid']

    try:
        api_post_request('catpile_api', '/fetch_to_run',
                         json.dumps({ 'fetch_uuid': fetch_uuid,
                                      'pipeline_run_uuid': run_uuid }))
    except Exception as e:
        logger.error("catpile failed linking fetch and run: {str(e)}")

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
        # catweb run uuid (not to be confused with the uuid generated by nextflow)
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
    logger.warning(f"data: {data}")
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

        fetch_given_input_b = ""
        fetch_uuid = ""

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

        if request.args.get('fetch_uuid'):
            fetch_uuid = request.args.get('fetch_uuid')

        ref_uuid = str()
        if request.args.get('ref_uuid'):
            ref_uuid = request.args.get('ref_uuid')

        logger.debug(sample_names)
        logger.debug(references)
        return render_template('start_run.template',
                               ref_uuid=ref_uuid,
                               flow_cfg=flow_cfg,
                               sample_names=sample_names,
                               references=references,
                               given_input=fetch_given_input,
                               fetch_given_input_b=fetch_given_input_b,
                               now=datetime.datetime.now().strftime("%Y%m%d_%H%M%S"),
                               user_param_dict=user_param_dict,
                               guessed_filename_format=guessed_filename_format,
                               fetch_uuid=fetch_uuid)

    elif request.method == 'POST':
        logger.debug('form: {0}'.format(request.form))
        new_run1(flow_name, flow_cfg, request.form)
        return redirect("/flow/{0}".format(flow_name))

@app.route('/map_samples', methods=['POST'])
@flask_login.login_required
def map_samples():
    if 'sample_names' in request.form:
        # display table
        if 'fetch_uuid' in request.form:
            fetch_uuid = request.form['fetch_uuid']
        else:
            fetch_uuid = ""
        return render_template('refmap.template',
                               sample_names=ast.literal_eval(request.form['sample_names']),
                               references=ast.literal_eval(request.form['references']),
                               flow_name=request.form['flow_name'],
                               fetch_given_input_b=request.form['fetch_given_input_b'],
                               fetch_uuid=fetch_uuid)
    else:
        # save results in database and redirect to new run
        reference_map = dict()
        logger.warning(str(request.form))
        for k,v in request.form.items():
            if k[0:5] == '_ref_':
                logger.debug(f'{k}={v}')
                sample_name = k[5:]
                reference = v
                reference_map[sample_name] = reference
        ref_uuid = str(uuid.uuid4())
        data = { 'ref_uuid': ref_uuid,
                 'reference_json': reference_map }
        if 'fetch_uuid' in request.form:
            fetch_uuid = request.form['fetch_uuid']
        else:
            fetch_uuid = ""

        logger.debug(f'form data: {data}')
        if 'cancel' in request.form:
            return redirect(f'/flow/{ request.form["flow_name"] }/new?given_input={ request.form["fetch_given_input_b"] }&fetch_uuid={ fetch_uuid }')
        else:
            api_post_request('nfweb_api', '/add_to_reference_cache', json.dumps(data))
            return redirect(f'/flow/{ request.form["flow_name"] }/new?given_input={ request.form["fetch_given_input_b"] }&ref_uuid={ ref_uuid }&fetch_uuid={ fetch_uuid }')

@app.route('/flow/<flow_name>')
@flask_login.login_required
def list_runs(flow_name : str):
    if flow_name in flows:
        flow_cfg = flows[flow_name]
    else:
        abort(404, description="Flow not found")

    response = api_get_request('nfweb_api', '/flow/{0}'.format(flow_name))
    data = response["data"]

    has_dagpng = False
    if pathlib.Path(f"/data/pipelines/dags/{flow_name}.png").is_file():
        has_dagpng = True

    return render_template('list_runs.template',
                           stuff={ 'display_name': flow_cfg['display_name'],'flow_name': flow_cfg['name'] },
                           has_dagpng=has_dagpng,
                           data=data)

@app.route('/flow/<flow_name>/dagpng')
@flask_login.login_required
def show_dagpng(flow_name : str):
    if not flow_name in flows:
        abort(404, description="Flow not found")

    dagpng_path = f"/data/pipelines/dags/{flow_name}.png"

    if not pathlib.Path(dagpng_path).is_file():
        abort(404, description="DAG png file not found")

    with open(dagpng_path, "rb") as f:
        dagpng_b64 = base64.b64encode(f.read()).decode()

    return render_template('show_dagpng.template',
                           flow_name=flow_name,
                           dagpng_b64=dagpng_b64)



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
    if not is_admin():
        abort(403)
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

@app.route('/storage_analysis')
@flask_login.login_required
def storage_analysis():
    try:
        with open('/db/catspace_result.txt') as f:
            catspace_result = json.loads(f.read())
        catspace_all_sorted = sorted(catspace_result, key=lambda row: row['du_run_space'] + row['du_output_space'], reverse=True)
    except Exception as e:
        logging.error(str(e))
        catspace_all_sorted = list()

    for row in catspace_all_sorted:
        row['total'] = row['du_run_space'] + row['du_output_space']

    total_used_run = sum([row['du_run_space'] for row in catspace_all_sorted])
    total_used_output = sum([row['du_output_space'] for row in catspace_all_sorted])

    return render_template('storage_analysis.template',
                           catspace_all_sorted=catspace_all_sorted,
                           total_used_run=total_used_run,
                           total_used_output=total_used_output)

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

@app.route('/drop_upload')
@flask_login.login_required
def upload_data():
    subfolder = str(uuid.uuid4())
    rootpath = pathlib.Path(f'/data/inputs/users/{ get_user_dict()["name"] }')
    newpath = str(rootpath / subfolder)
    newpath_encoded = base64.b16encode(bytes(newpath, encoding='utf-8')).decode('utf-8')

    return render_template('upload.template',
                           subfolder=subfolder,
                           fetchpath=newpath,
                           fetchpath_encoded=newpath_encoded)

@app.route('/drop_upload/<subfolder>', methods=['POST'])
@flask_login.login_required
def upload_data2(subfolder):
    file = request.files['file']
    if file.filename[-9:] == '.fastq.gz' or file.filename[-4:] == '.bam':
        rootpath = pathlib.Path(f'/data/inputs/users/{ get_user_dict()["name"] }')
        newpath = str(rootpath / subfolder)
        logger.warning(newpath)
        if not (os.path.isdir(newpath)):
            os.mkdir(newpath)
        save_path = os.path.join(newpath, secure_filename(file.filename))
        logger.warning(save_path)
        with open(save_path, 'ab') as f:
            f.seek(int(request.form['dzchunkbyteoffset']))
            f.write(file.stream.read())
        return make_response(('Uploaded Chunk', 200))
    else:
        return make_response(('File format not permitted', 415))

@app.route('/fetch_data')
@flask_login.login_required
def fetch_data():
    r = api_get_request('fetch_api', '/api/fetch/describe')
    sources = r['sources']

    return render_template('new_fetch.template', sources=sources)

@app.route('/get_files', methods=['POST'])
@flask_login.login_required
def get_files():
    from flask import jsonify
    req = request.get_json()
    if 'path' not in req:
        abort(403)
    path = req['path']
    #return json.dumps([str(x.name) for x in pathlib.Path(path).glob('*')])
    filenames = os.listdir(path)
    dict_filenames = dict(filenames=filenames)
    return jsonify(dict_filenames)

def get_user_dict():
    return users[flask_login.current_user.id]

@app.route('/fetch_data2/<fetch_kind>')
@flask_login.login_required
def fetch_data2(fetch_kind):
    r = api_get_request('fetch_api', '/api/fetch/describe')
    source = r['sources'][fetch_kind]

    # allow prefilling of the new fetch form
    in_data_kind = None
    in_data_identifier = None

    if 'kind' in request.args and 'id' in request.args:
        in_data_kind = request.args.get('kind')
        in_data_identifier = request.args.get('id')
        in_data_identifier = base64.b16decode(in_data_identifier).decode('utf-8')

    paths = list()
    if 'local_glob_directories' in source:
        for d in source['local_glob_directories']:
            if authenticate.user_can_see_upload_dir(get_user_dict(), d):
                for p in glob.glob(d):
                    paths.append(p)
        paths.sort()

    if fetch_kind == 'ena1':
        return render_template('new_fetch2_ena1.template',
                               source=source,
                               fetch_kind=fetch_kind,
                               data_kind=in_data_kind,
                               data_identifier=in_data_identifier,
                               paths=paths)
    if fetch_kind == 'local1':
        return render_template('new_fetch2_local1.template',
                               source=source,
                               fetch_kind=fetch_kind,
                               data_kind=in_data_kind,
                               data_identifier=in_data_identifier,
                               paths=paths)
    abort(404)

@app.route('/fetch')
@flask_login.login_required
def fetch():
    r = api_get_request('fetch_api', '/api/fetch/status')
    r2 = api_get_request('fetch_api', '/api/fetch/describe')

    sources = r2['sources']

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

    # filter fetches by what the user can see
    fetches = { k:v for k,v in fetches.items() if authenticate.is_public_fetch_source(v['kind']) or authenticate.user_can_see_upload_dir(get_user_dict(), v['name']) }

    # sort fetches by time
    fetches = dict(reversed(sorted(fetches.items(), key=lambda x: authenticate.is_public_fetch_source(x[1]['started']))))

    return render_template('fetch.template', fetches=fetches, sources=sources)

@app.route('/fetch_new')
@flask_login.login_required
def fetch_new():
    fetch_name = request.args.get("fetch_name")
    fetch_range = request.args.get("fetch_range")
    fetch_kind = request.args.get("fetch_kind")
    fetch_method = request.args.get("fetch_method")

    # base16 encode path to avoid / in url
    fetch_name_b = base64.b16encode(bytes(fetch_name, encoding='utf-8')).decode('utf-8')

    url = f"/api/fetch/{fetch_kind}/new/{fetch_name_b}?fetch_range={fetch_range}&fetch_method={fetch_method}"
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

    flow_name = None
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

    user_pipelines = get_user_pipelines(flask_login.current_user.id)
    if not flow_name:
        if user_pipelines:
            flow_name = list(user_pipelines)[0]

    return render_template('select_flow.template',
                           guid=guid,
                           name=accession,
                           fetch_range=fetch_range,
                           status=status,
                           progress=progress,
                           total=total,
                           flow_name=flow_name,
                           input_dir=input_dir,
                           output_dir_b16=output_dir_b16,
                           user_pipelines=user_pipelines)

@app.route('/flow/<flow_name>/show_metadata/<pipeline_run_uuid>')
@flask_login.login_required
def fetch_metadata(flow_name, pipeline_run_uuid):
    sp3data = api_get_request('catpile_api', f'/get_sp3_data_for_run/{pipeline_run_uuid}')
    sp3data = list(enumerate(sp3data))

    return render_template('show_sp3data.template',
                           pipeline_run_uuid=pipeline_run_uuid,
                           sp3data=sp3data)

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
    sp3data = None
    if 'ena' in ret2 and ret2['ena']:
        logger.debug(ret2['ena'][:80])
        pandas.set_option('display.max_colwidth', -1)
        ena_table = pandas.read_json(ret2['ena']).stack().sort_index().to_frame().to_html()
    else:
        sp3data = api_get_request('catpile_api', f'/get_sp3_data_for_fetch/{guid}')
        sp3data = list(enumerate(sp3data))

    return render_template('fetch_details.template',
                           guid=guid,
                           name=accession,
                           fetch_range=fetch_range,
                           status=status,
                           progress=progress,
                           total=total,
                           file_table=file_table,
                           log=app_log,
                           input_dir=input_dir,
                           ena_table=ena_table,
                           sp3data=sp3data)

@app.route('/flow/<run_uuid>/<dataset_id>/report')
@flask_login.login_required
def get_report(run_uuid : str, dataset_id: str):
    # TODO add API config
    resp = api_get_request('report_api', f'/report/{run_uuid}/{dataset_id}')
    catpile_resp = api_get_request('catpile_api', f'/get_sp3_data_for_run_sample/{run_uuid}/{dataset_id}')
    report_data = resp['report_data'] # data in from catreport

    import reportlib
    template_report_data = reportlib.process_reports(report_data, catpile_resp, cfg.get('download_url'))

    return render_template('report.template',
                           pipeline_run_uuid=run_uuid,
                           dataset_id=dataset_id,
                           report=template_report_data)

@app.route('/cw_query')
@flask_login.login_required
def cw_query():
    msg = ""
    all_runs = dict()
    neighbours = list()

    run_id = request.args.get('run_id')
    sample_name = request.args.get('sample_name')
    distance = request.args.get('distance')
    neighbours_ok = False

    if not (run_id and sample_name and distance):
        return render_template('cw_query.template',
                               distance = 12)

    else:
        # call persistence API to get run-name map
        combine_name = run_id + '_' + sample_name
        res = requests.get(f'https://persistence.mmmoxford.uk/api_cw_get_neighbours/{combine_name}/{distance}')
        message = res.text
        logger.debug(f'catwalk returned: {res.text}')
        try:
            neighbours = res.json()
            neighbours_ok = True
            all_runs = requests.get(f'https://persistence.mmmoxford.uk/api_get_runs_name_map').json()
            message = ""
        except:
            pass

        return render_template('cw_query.template',
                               neighbours_ok = neighbours_ok,
                               all_runs = all_runs,
                               run_id = run_id,
                               sample_name = sample_name,
                               distance = distance,
                               message = message,
                               neighbours = neighbours )

@app.route('/get_cluster_stats')
def proxy_get_cluster_stats():
    response = api_get_request('catstat_api', '/data')
    return json.dumps(response)


def main():
    app.run(port=7000)

if __name__ == "__main__":
    main()
