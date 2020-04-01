import json, sqlite3, sys
import pathlib
import csv

import requests, yaml
from flask import Flask, request

config = yaml.load(open('config.yaml').read())

con = sqlite3.connect(config['db_target'], check_same_thread=False)

con.execute("create table if not exists fetch_to_run (fetch_uuid, pipeline_run_uuid);")
con.execute("create table if not exists sp3_data (fetch_uuid, submission_uuid4, sample_uuid4, sample_index, subindex, sample_filename, sample_file_extension, sample_host, sample_collection_date, sample_country, submission_title, submission_description, submitter_organisation, submitter_email, instrument_platform, instrument_model, instrument_flowcell, original_file_md5, original_file_sha1, original_file_sha512, clean_file_md5, clean_file_sha1, clean_file_sha512);")

app = Flask(__name__)

@app.route('/get_runs_for_fetch/<fetch_uuid>')
def get_runs_for_fetch(fetch_uuid):
    rows = con.execute("select pipeline_run_uuid from fetch_to_run where fetch_uuid = ?", (fetch_uuid,))
    return json.dumps([row[0] for row in rows])

@app.route('/get_fetch_for_run/<pipeline_run_uuid>')
def get_fetch_for_run(pipeline_run_uuid):
    rows = con.execute("select fetch_uuid from fetch_to_run where pipeline_run_uuid = ?", (pipeline_run_uuid,)).fetchall()
    if rows:
        return json.dumps(rows[0][0])
    else:
        return json.dumps(None)

@app.route('/get_sp3_data_for_fetch/<fetch_uuid>')
def get_sp3_data_for_fetch(fetch_uuid):
    con.row_factory = sqlite3.Row
    rows = con.execute("select * from sp3_data where fetch_uuid = ?", (fetch_uuid,)).fetchall()
    con.row_factory = None
    data = [dict(row) for row in rows]
    return json.dumps({ 'status': 'success',
                        'data': data,
                        'message': None })

@app.route('/get_sp3_data_for_run/<pipeline_run_uuid>')
def get_sp3_data_for_run(pipeline_run_uuid):
    fetch_uuid = json.loads(get_fetch_for_run(pipeline_run_uuid))
    if fetch_uuid:
        return get_sp3_data_for_fetch(fetch_uuid)
    else:
        return json.dumps({ 'status': 'success',
                            'data': [],
                            'message': None })

@app.route('/fetch_to_run', methods=['POST'])
def fetch_to_run():
    j = request.json
    if not 'fetch_uuid' in j or not 'pipeline_run_uuid' in j:
        abort(400)
    fetch_uuid = j['fetch_uuid']
    pipeline_run_uuid = j['pipeline_run_uuid']

    link_data(fetch_uuid, pipeline_run_uuid)

def link_data(fetch_uuid, pipeline_run_uuid):
    con.execute(f"insert into fetch_to_run values (?,?)", (fetch_uuid, pipeline_run_uuid))
    con.commit()

@app.route('/load_sp3_data/', methods=['POST'])
def load_sp3_data():
    j = request.json
    if not 'fetch_uuid' in j or not 'fetch_dir' in j:
        abort(404)
    fetch_uuid = j['fetch_uuid']
    fetch_dir = j['fetch_dir']

    add_data(fetch_uuid, fetch_dir)

def add_data(fetch_uuid, fetch_dir):
    sp3data_filepath = pathlib.Path(fetch_dir) / 'sp3data.csv'
    if not sp3data_filepath.exists():
        abort(404)

    with open(sp3data_filepath) as f:
        reader = csv.reader(f)
        next(reader)
        for row in reader:
            question_marks = ",".join("?" * (len(row)+1))
            con.execute(f"insert into sp3_data values ({question_marks})", (fetch_uuid, *row))
        con.commit()

if __name__ == '__main__':
    if sys.argv[1] == 'add':
        add_data(sys.argv[2], sys.argv[3])
    elif sys.argv[1] == 'link':
        link_data(sys.argv[2], sys.argv[3])
    else:
        app.run(port=22000)
