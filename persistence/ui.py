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
from flask import Flask, request, render_template, redirect
import flask_login
import yaml

import authenticate
import getreportlib
import reportlib

app = Flask(__name__)
app.secret_key = 'secret key'

login_manager = flask_login.LoginManager()
login_manager.init_app(app)
login_manager.login_view = '/login'

class User(flask_login.UserMixin):
    pass

users = dict()

@login_manager.user_loader
def user_loader(username):
    if username not in users:
        return
    user = User()
    user.id = username
    return user

auth_ldap = dict()
cfg = yaml.load(open('config.yaml').read())
for l in cfg["auth_ldap"]:
    auth_ldap[l['name']] = l

@app.route('/logout')
def logout():
    flask_login.logout_user()
    return redirect('/login')

def get_user_dict():
    return users[flask_login.current_user.id]

def get_user_organisation():
    if 'organisations' not in cfg:
        logging.error("config doesn't have organisations")
        logging.error(str(cfg))
        return None
    u = get_user_dict()
    for org in cfg['organisations']:
        if 'users' in org and u['name'] in org['users']:
            return org['name']
    logging.warning("user not in any organisation")

def is_admin():
    try:
        return 'admin' in users[flask_login.current_user.id]['capabilities']
    except:
        return False

def org_can_see_pipeline(org_name, pipeline_name):
    if is_admin():
        return True
    else:
        return pipeline_name[0:len(org_name)+1] == org_name + "-"

def org_filter_runs(org_name, runs):
    ret = list()
    for run in runs:
        if org_can_see_pipeline(org_name, run[9]):
            ret.append(run)
    return ret

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.template')
    if request.method == 'POST':
        if not 'username' in request.form or not 'password' in request.form:
            logging.warning(f"form submitted without username or password")
            return redirect('/')

        form_username = request.form['username']
        form_password = request.form['password']

        for ldap_domain, ldap_dict in auth_ldap.items():
            if form_username in ldap_dict['authorized_users']:
                auth_cfg = ldap_dict
                ldap_host = auth_cfg['host']
                is_ok = authenticate.check_ldap_authentication(form_username, form_password, ldap_host)
                if is_ok:
                    print(f"user {form_username} verified for ldap host {ldap_host}")
                    break
                else:
                    print(f"invalid credentials for ldap user {form_username} host {ldap_host}")
                    return redirect('/')
        else:
            logger.warning(f"user {form_username} is not in ldap authorized_users list")
            return redirect('/')

        '''
        User is authorized
        '''
        user = User()
        user.id = form_username
        flask_login.login_user(user)

        cap = list()
        if form_username in auth_cfg['admins']:
            cap = ['admin']

        users[user.id] = {
            'name': form_username,
            'capabilities': cap
        }

        return redirect('/list_instances')

    assert False, "unreachable"

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
    return redirect('/login')

# --- api ---

runs_name_map_json_str = str()

def make_runs_name_map():
    runs_name_map = dict()
    for instance in get_instances('/work/persistence'):
        instance_id = instance['id']
        with sqlite3.connect(f'/work/persistence/{instance_id}/db/catweb.sqlite') as con:
            for row in con.execute("select run_uuid, output_name from nfruns"):
                run_uuid = row[0]
                run_name = row[1]

                runs_name_map[run_uuid] = {
                    'instance_name': instance['name'],
                    'instance_id': instance_id,
                    'run_name': run_name
                }

    global runs_name_map_json_str
    runs_name_map_json_str = json.dumps(runs_name_map)

make_runs_name_map()

@app.route("/api_get_runs_name_map")
def api_get_runs_name_map():
    return runs_name_map_json_str

@app.route("/api_cw_get_neighbours/<run_uuid_and_sample_name>/<snp_distance>")
def api_cw_get_neighbours(run_uuid_and_sample_name, snp_distance):
    return requests.get(f"http://localhost:5000/neighbours/{ run_uuid_and_sample_name }/{ snp_distance }").text

@app.route('/api_submit_tree', methods=["POST"])
def submit_tree():
    return requests.post('http://localhost:7654/submit_tree', json=request.json).text

@app.route('/api_list_trees')
def list_trees():
    return requests.get('http://localhost:7654/list_trees', params=request.args).text

@app.route('/api_get_tree/<guid>')
def get_tree(guid):
    return requests.get(f"http://localhost:7654/get_tree/{ guid }").text





# ---- ui ---
@app.route('/list_instances')
@flask_login.login_required
def list_instances():
    labkey_url = 'http://labkey.oxfordfun.com'
    instances = get_instances('/work/persistence')
    instances.sort(key = lambda x: 'status' in x and x['status'] == 'down')

    return render_template('main.template',
                           instances=instances,
                           labkey_url=labkey_url)

@app.route('/cluster_browse/<cluster_id>')
@flask_login.login_required
def browse(cluster_id):
    cluster_info = get_instance('/work/persistence', cluster_id)

    con = sqlite3.connect(f'/work/persistence/{cluster_id}/db/catweb.sqlite')
    runs = con.execute('select * from nfruns  where status="OK" order by start_epochtime desc').fetchall()
    runs = org_filter_runs(get_user_organisation(), runs)

    return render_template('cluster_browse.template',
                           runs=runs,
                           cluster_id=cluster_id,
                           cluster_info=cluster_info)

@app.route('/report/<cluster_uuid>/<run_uuid>/<dataset_id>')
@flask_login.login_required
def get_report(cluster_uuid, run_uuid, dataset_id):
    catpile_resp = None
    report_data = getreportlib.get_report(cluster_uuid,
                                          None,
                                          run_uuid,
                                          dataset_id)['data']['report_data']

    template_report_data = reportlib.process_reports(report_data, catpile_resp, "")

    return render_template('report.template',
                           pipeline_run_uuid=run_uuid,
                           dataset_id=dataset_id,
                           report=template_report_data)

@app.route('/cluster_run_details/<cluster_id>/<run_uuid>')
@flask_login.login_required
def cluster_run_details(cluster_id, run_uuid):
    cluster_info = get_instance('/work/persistence', cluster_id)

    output_dir = pathlib.Path('/work') / 'persistence' / cluster_id / 'work' / 'output' / run_uuid
    output_dir_exists = output_dir.is_dir()

    nextflow_log = pathlib.Path('/work') / 'persistence' / cluster_id / 'work' / 'runs' / run_uuid / '.nextflow.log'
    nextflow_log_exists = nextflow_log.is_file()

    con = sqlite3.connect(f'/work/persistence/{cluster_id}/db/catweb.sqlite')
    con.row_factory = sqlite3.Row
    run = con.execute('select * from nfruns where run_uuid = ?', (run_uuid,)).fetchone()
    run_json_data = json.loads(run['data_json'])

    run = dict(run)

    con2 = sqlite3.connect(f'/work/persistence/{cluster_id}/db/catreport.sqlite')
    con2.row_factory = sqlite3.Row
    reports = con2.execute('select distinct sample_name from q where pipeline_run_uuid = ?', (run_uuid,)).fetchall()

    for report in reports:
        try:
            report['finished_time_str'] = time.strftime("%Y/%m/%d %H:%M",
                                                        time.localtime(int(report['finished_epochtime'])))
        except:
            # report queued/running
            pass

    return render_template('cluster_run_details.template',
                           run=run,
                           run_json_data=run_json_data,
                           cluster_info=cluster_info,
                           reports=reports,
                           output_dir_exists=output_dir_exists,
                           nextflow_log_exists=nextflow_log_exists)

def main():
    app.run(port=11000)

if __name__ == '__main__':
    main()
