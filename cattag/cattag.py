import sqlite3
import json
import yaml

from flask import Flask, request
import waitress

with open('config.yaml') as f:
    config = yaml.load(f.read())

con = sqlite3.connect('/db/cattag.sqlite', check_same_thread=False)

con.execute('create table if not exists run_tags (pipeline_name, run_uuid, tag_type, tag_name, unique(pipeline_name, run_uuid, tag_type, tag_name))')
con.execute('create table if not exists sample_tags (pipeline_name, run_uuid, sample_name, tag_type, tag_name, unique(pipeline_name, run_uuid, sample_name, tag_type, tag_name))')

app = Flask(__name__)

@app.route('/add_run_tag', methods=['POST'])
def add_run_tag():
    data = request.json
    ins = (data['pipeline_name'], data['run_uuid'], data['tag_type'], data['tag_name'])
    con.execute('insert or ignore into run_tags values (?, ?, ?, ?)', ins)
    con.commit()
    return "ok"

@app.route('/add_sample_tag', methods=['POST'])
def add_sample_tag():
    data = request.json
    ins = (data['pipeline_name'], data['run_uuid'], data['sample_name'], data['tag_type'], data['tag_name'])
    con.execute('insert or ignore into sample_tags values (?, ?, ?, ?, ?)', ins)
    con.commit()
    return "ok"

def make_api_response(status, details=None, data=None):
    return json.dumps({ 'status': status,
                        'details': details,
                        'data': data })

@app.route('/get_run_tags/<pipeline_name>/<run_uuid>')
def get_run_tags(pipeline_name, run_uuid):
    data = con.execute('select pipeline_name, run_uuid, tag_type, tag_name from run_tags where pipeline_name = ? and run_uuid = ?', (pipeline_name, run_uuid,)).fetchall()
    return make_api_response(status = 'success',
                             details = None,
                             data = data)

@app.route('/get_sample_tags_for_run/<run_uuid>')
def get_sample_tags_for_run(run_uuid):
    data = con.execute('select sample_name, tag_type, tag_name from sample_tags where run_uuid = ?', (run_uuid,)).fetchall()
    return make_api_response(status = 'success',
                             details = None,
                             data = data)

@app.route('/get_sample_tags/<run_uuid>/<sample_name>')
def get_sample_tags(run_uuid, sample_name):
    data = con.execute('select run_uuid, tag_type, tag_name from sample_tags where run_uuid = ? and sample_name = ?', (run_uuid,sample_name)).fetchall()
    return make_api_response(status = 'success',
                             details = None,
                             data = data)

if __name__ == '__main__':
    waitress.serve(app, listen=f"{ config['bind_host'] }:12000")
