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

        users[user.id] = {
            'name': form_username,
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
    runs = con.execute('select * from nfruns order by start_epochtime desc').fetchall()
    return render_template('cluster_browse.template',
                           runs=runs,
                           cluster_id=cluster_id,
                           cluster_info=cluster_info)

@app.route('/cluster_run_details/<cluster_id>/<run_uuid>')
@flask_login.login_required
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
