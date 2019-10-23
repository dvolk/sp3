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
from flask import request
import yaml

import resistance_help

with open('catreport.yaml') as f:
    config = yaml.load(f.read())

app = flask.Flask(__name__)

def epochtime():
    return str(int(time.time()))

con = sqlite3.connect(config['db_target'], check_same_thread=False)
con.execute('create table if not exists q (uuid primary key, type, status, added_epochtime, started_epochtime, finished_epochtime, pipeline_run_uuid, sample_name, sample_filepath, report_filename, software_versions)')
con.execute('create index if not exists q_pipeline_uuids on q (pipeline_run_uuid)')
con.execute('create index if not exists q_type on q (type)')
con.execute('create index if not exists q_status on q (status)')

sql_lock = threading.Lock()

@app.route('/req_report/', methods=['POST'])
def req_report():
    '''
    Request a report

    It is added to the queue and processed one by one

    Mandatory inputs: pipeline run uuid, sample name, sample path, report type
    '''
    print(request.data)
    data = json.loads(request.data.decode('utf-8'))
    pipeline_run_uuid = data['pipeline_run_uuid']
    sample_name = data['sample_name']
    sample_filepath = data['sample_filepath']
    report_type = data['report_type']

    report_uuid = str(uuid.uuid4())
    report_status = 'queued'
    report_added_epochtime = epochtime()

    report_started_epochtime = str()
    report_finished_epochtime = str()
    report_filename = str()
    software_versions = str()

    new_row = (report_uuid, report_type, report_status, report_added_epochtime, report_started_epochtime,
               report_finished_epochtime, pipeline_run_uuid, sample_name, sample_filepath, report_filename, software_versions)

    with sql_lock, con:
        con.execute('insert into q values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', new_row)

    report_started_epochtime = epochtime()

    return "queued"

def get_report_for_type(pipeline_run_uuid, sample_name, report_type):
    '''
    Query database for report

    Mandatory inputs: pipeline run uuid, sample name, report type
    '''
    with sql_lock, con:
        r = con.execute('select * from q where status = "done" and pipeline_run_uuid = ? and sample_name = ? and type = ? order by added_epochtime desc',
                        (pipeline_run_uuid,
                         sample_name,
                         report_type
                        )).fetchall()
    if r:
        return r[0]
    else:
        return None

def resistance_thread(con):
    '''
    Process that monitors the queue for resistance api requests
    '''
    while True:
        with sql_lock, con:
            rows = con.execute("select * from q where status = 'queued' and type = 'resistance' order by added_epochtime asc limit 1").fetchall()
        if rows:
            row = rows[0]
            report_uuid = row[0]
            sample_filepath = row[8]

            report_started_epochtime = epochtime()
            print(f"resistance_thread: working on {report_uuid} ({sample_filepath})")
            report_filename = make_resistance_report(report_uuid, sample_filepath)
            print(f"resistance_thread: finished with {report_uuid}")
            report_status = 'done'
            report_finished_epochtime = epochtime()

            with sql_lock, con:
                con.execute("update q set report_filename = ?, started_epochtime = ?, finished_epochtime = ?, status = ? where uuid = ?",
                            (report_filename,
                             report_started_epochtime,
                             report_finished_epochtime,
                             report_status,
                             report_uuid
                            ))

        time.sleep(5)

def mykrobe_speciation_thread(con):
    '''
    Process that monitors the queue for resistance api requests
    '''
    while True:
        with sql_lock, con:
            rows = con.execute("select * from q where status = 'queued' and type = 'mykrobe_speciation' order by added_epochtime asc limit 1").fetchall()
        if rows:
            row = rows[0]
            report_uuid = row[0]
            sample_filepath = row[8]

            report_started_epochtime = epochtime()
            print(f"mykrobe_speciation_thread: working on {report_uuid} ({sample_filepath})")
            report_filename = make_mykrobe_speciation_report(report_uuid, sample_filepath)
            print(f"mykrobe_speciation_thread: finished with {report_uuid}")
            report_status = 'done'
            report_finished_epochtime = epochtime()

            with sql_lock, con:
                con.execute("update q set report_filename = ?, started_epochtime = ?, finished_epochtime = ?, status = ? where uuid = ?",
                            (report_filename,
                             report_started_epochtime,
                             report_finished_epochtime,
                             report_status,
                             report_uuid
                            ))

        time.sleep(5)

def pick_reference_thread(con):
    '''
    Process that monitors the queue for resistance api requests
    '''
    while True:
        with sql_lock, con:
            rows = con.execute("select * from q where status = 'queued' and type = 'pick_reference' order by added_epochtime asc limit 1").fetchall()
        if rows:
            row = rows[0]
            report_uuid = row[0]
            sample_filepath = row[8]

            report_started_epochtime = epochtime()
            print(f"pick_reference_thread: working on {report_uuid} ({sample_filepath})")
            report_filename = make_pick_reference_report(report_uuid, sample_filepath)
            print(f"pick_reference_thread: finished with {report_uuid}")
            report_status = 'done'
            report_finished_epochtime = epochtime()

            with sql_lock, con:
                con.execute("update q set report_filename = ?, started_epochtime = ?, finished_epochtime = ?, status = ? where uuid = ?",
                            (report_filename,
                             report_started_epochtime,
                             report_finished_epochtime,
                             report_status,
                             report_uuid
                            ))

        time.sleep(5)

def kraken2_speciation_thread(con):
    '''
    Process that monitors the queue for resistance api requests
    '''
    while True:
        with sql_lock, con:
            rows = con.execute("select * from q where status = 'queued' and type = 'kraken2_speciation' order by added_epochtime asc limit 1").fetchall()
        if rows:
            row = rows[0]
            report_uuid = row[0]
            sample_filepath = row[8]

            report_started_epochtime = epochtime()
            print(f"pick_reference_thread: working on {report_uuid} ({sample_filepath})")
            report_filename = make_kraken2_speciation_report(report_uuid, sample_filepath)
            print(f"pick_reference_thread: finished with {report_uuid}")
            report_status = 'done'
            report_finished_epochtime = epochtime()

            with sql_lock, con:
                con.execute("update q set report_filename = ?, started_epochtime = ?, finished_epochtime = ?, status = ? where uuid = ?",
                            (report_filename,
                             report_started_epochtime,
                             report_finished_epochtime,
                             report_status,
                             report_uuid
                            ))

        time.sleep(5)

def nfnvm_nanostats_qc_thread(con):
    '''
    Process that monitors the queue for nfnvm nano stats qc requests
    '''
    while True:
        with sql_lock, con:
            rows = con.execute("select * from q where status = 'queued' and type = 'nfnvm_nanostats_qc' order by added_epochtime asc limit 1").fetchall()
        if rows:
            row = rows[0]
            report_uuid = row[0]
            sample_filepath = row[8]

            report_started_epochtime = epochtime()
            print(f"pick_reference_thread: working on {report_uuid} ({sample_filepath})")
            report_filename = make_nfnvm_nanostats_qc_report(report_uuid, sample_filepath)
            print(f"pick_reference_thread: finished with {report_uuid}")
            report_status = 'done'
            report_finished_epochtime = epochtime()

            with sql_lock, con:
                con.execute("update q set report_filename = ?, started_epochtime = ?, finished_epochtime = ?, status = ? where uuid = ?",
                            (report_filename,
                             report_started_epochtime,
                             report_finished_epochtime,
                             report_status,
                             report_uuid
                            ))

        time.sleep(5)

def nfnvm_flureport_thread(con):
    '''
    Process that monitors the queue for nfnvm nano stats qc requests
    '''
    while True:
        with sql_lock, con:
            rows = con.execute("select * from q where status = 'queued' and type = 'nfnvm_flureport' order by added_epochtime asc limit 1").fetchall()
        if rows:
            row = rows[0]
            report_uuid = row[0]
            sample_filepath = row[8]

            report_started_epochtime = epochtime()
            print(f"pick_reference_thread: working on {report_uuid} ({sample_filepath})")
            report_filename = make_nfnvm_flureport_report(report_uuid, sample_filepath)
            print(f"pick_reference_thread: finished with {report_uuid}")
            report_status = 'done'
            report_finished_epochtime = epochtime()

            with sql_lock, con:
                con.execute("update q set report_filename = ?, started_epochtime = ?, finished_epochtime = ?, status = ? where uuid = ?",
                            (report_filename,
                             report_started_epochtime,
                             report_finished_epochtime,
                             report_status,
                             report_uuid
                            ))

        time.sleep(5)

def nfnvm_viralreport_thread(con):
    '''
    Process that monitors the queue for nfnvm nano stats qc requests
    '''
    while True:
        with sql_lock, con:
            rows = con.execute("select * from q where status = 'queued' and type = 'nfnvm_viralreport' order by added_epochtime asc limit 1").fetchall()
        if rows:
            row = rows[0]
            report_uuid = row[0]
            sample_filepath = row[8]

            report_started_epochtime = epochtime()
            print(f"pick_reference_thread: working on {report_uuid} ({sample_filepath})")
            report_filename = make_nfnvm_viralreport_report(report_uuid, sample_filepath)
            print(f"pick_reference_thread: finished with {report_uuid}")
            report_status = 'done'
            report_finished_epochtime = epochtime()

            with sql_lock, con:
                con.execute("update q set report_filename = ?, started_epochtime = ?, finished_epochtime = ?, status = ? where uuid = ?",
                            (report_filename,
                             report_started_epochtime,
                             report_finished_epochtime,
                             report_status,
                             report_uuid
                            ))

        time.sleep(5)

def samtools_qc_thread(con):
    '''
    Process that monitors the queue for samtools qc requests
    '''
    while True:
        with sql_lock, con:
            rows = con.execute("select * from q where status = 'queued' and type = 'samtools_qc' order by added_epochtime asc limit 1").fetchall()
        if rows:
            row = rows[0]
            report_uuid = row[0]
            sample_filepath = row[8]

            report_started_epochtime = epochtime()
            print(f"pick_reference_thread: working on {report_uuid} ({sample_filepath})")
            report_filename = make_samtools_qc_report(report_uuid, sample_filepath)
            print(f"pick_reference_thread: finished with {report_uuid}")
            report_status = 'done'
            report_finished_epochtime = epochtime()

            with sql_lock, con:
                con.execute("update q set report_filename = ?, started_epochtime = ?, finished_epochtime = ?, status = ? where uuid = ?",
                            (report_filename,
                             report_started_epochtime,
                             report_finished_epochtime,
                             report_status,
                             report_uuid
                            ))

        time.sleep(5)
        
def make_resistance_report(report_uuid, sample_filepath):
    '''
    1. symlink sample file path to /work/reports/resistanceapi/vcfs/{report_uuid}.vcf
    2. send request for report to resistance api
    3. write report to /work/reports/catreport/reports/{report_uuid}.json
    4. delete symlink from 1.
    '''
    os.system(f'cd /work/reports/resistanceapi/vcfs; ln -s {sample_filepath} {report_uuid}.vcf')
    url = f'http://localhost:8990/api/v1/resistances/piezo/{report_uuid}?type=piezo'
    print(url)
    r = requests.get(url)
    print(r.text)
    out_filepath = f'/work/reports/catreport/reports/{report_uuid}.json'
    with open(out_filepath, 'w') as report_file:
        report_file.write(r.text)
    os.system(f'cd /work/reports/resistanceapi/vcfs && rm {report_uuid}.vcf')
    return out_filepath

def make_mykrobe_speciation_report(report_uuid, sample_filepath):
    out_filepath = f'/work/reports/catreport/reports/{report_uuid}.json'
    os.system(f'cp {sample_filepath} {out_filepath}')
    return out_filepath

def make_kraken2_speciation_report(report_uuid, sample_filepath):
    out_filepath = f'/work/reports/catreport/reports/{report_uuid}.json'
    os.system(f'cp {sample_filepath} {out_filepath}')
    return out_filepath

def make_pick_reference_report(report_uuid, sample_filepath):
    out_filepath = f'/work/reports/catreport/reports/{report_uuid}.json'
    os.system(f'cp {sample_filepath} {out_filepath}')
    return out_filepath

def make_samtools_qc_report(report_uuid, sample_filepath):
    out_filepath = f'/work/reports/catreport/reports/{report_uuid}.json'
    os.system(f'cp {sample_filepath} {out_filepath}')
    return out_filepath

def make_nfnvm_nanostats_qc_report(report_uuid, sample_filepath):
    out_filepath = f'/work/reports/catreport/reports/{report_uuid}.json'
    os.system(f'cp {sample_filepath} {out_filepath}')
    return out_filepath

def make_nfnvm_flureport_report(report_uuid, sample_filepath):
    out_filepath = f'/work/reports/catreport/reports/{report_uuid}.json'
    os.system(f'cp {sample_filepath} {out_filepath}')
    return out_filepath

def make_nfnvm_viralreport_report(report_uuid, sample_filepath):
    out_filepath = f'/work/reports/catreport/reports/{report_uuid}.json'
    os.system(f'cp {sample_filepath} {out_filepath}')
    return out_filepath

@app.route('/report/<pipeline_run_uuid>/<sample_name>')
def get_report(pipeline_run_uuid, sample_name):
    '''
    Get a report (all reports combined) for 1 sample
    '''

    '''
    begin resistance report
    '''
    r = get_report_for_type(pipeline_run_uuid, sample_name, 'resistance')
    report_resistance_data = dict()
    if r:
        report_resistance_guid = r[0]
        report_resistance_filepath = f"/work/reports/catreport/reports/{report_resistance_guid}.json"
        logging.warning(report_resistance_filepath)
        try:
            with open(report_resistance_filepath) as f:
                report_resistance_data = json.loads(f.read())['data']
            report_resistance_data['finished_epochtime'] = int(r[5])

            sources = dict()
            for i, item in enumerate(report_resistance_data['effects']):
                mut = item['gene_name'] + '_' + item['mutation_name']
                drug = item['drug_name']
                source = resistance_help.gene_to_source(mut, drug)[1]
                report_resistance_data['effects'][i]['source'] = source

        except Exception as e:
            logging.error("couldn't load resistance file as json")
            logging.error(str(e))
            report_resistance_data = dict()

    '''
    end resistance report
    '''

    '''
    begin speciation report
    '''
    r = get_report_for_type(pipeline_run_uuid, sample_name, 'mykrobe_speciation')
    report_mykrobe_speciation_data = dict()
    if r:
        report_mykrobe_speciation_guid = r[0]
        report_mykrobe_speciation_filepath = f"/work/reports/catreport/reports/{report_mykrobe_speciation_guid}.json"
        logging.warning(report_mykrobe_speciation_filepath)

        with open(report_mykrobe_speciation_filepath) as f:
            report_mykrobe_speciation_data = json.loads(f.read())
        report_mykrobe_speciation_data['finished_epochtime'] = int(r[5])
    '''
    end speciation report
    '''

    '''
    begin speciation report
    '''
    r = get_report_for_type(pipeline_run_uuid, sample_name, 'kraken2_speciation')
    report_kraken2_speciation_data = dict()
    if r:
        report_kraken2_speciation_guid = r[0]
        report_kraken2_speciation_filepath = f"/work/reports/catreport/reports/{report_kraken2_speciation_guid}.json"
        logging.warning(report_kraken2_speciation_filepath)

        with open(report_kraken2_speciation_filepath) as f:
            report_kraken2_speciation_data['tsv'] = f.read()
        report_kraken2_speciation_data['finished_epochtime'] = int(r[5])
    '''
    end speciation report
    '''

    '''
    begin pick reference report
    '''
    r = get_report_for_type(pipeline_run_uuid, sample_name, 'pick_reference')
    report_pick_reference_data = dict()
    if r:
        report_pick_reference_guid = r[0]
        report_pick_reference_filepath = f"/work/reports/catreport/reports/{report_pick_reference_guid}.json"
        logging.warning(report_pick_reference_filepath)

        with open(report_pick_reference_filepath) as f:
            report_pick_reference_data = json.loads(f.read())
        report_pick_reference_data['finished_epochtime'] = int(r[5])
    '''
    end speciation report
    '''

    '''
    begin samtools qc report
    '''
    r = get_report_for_type(pipeline_run_uuid, sample_name, 'samtools_qc')
    report_samtools_qc_data = dict()
    if r:
        report_samtools_qc_guid = r[0]
        report_samtools_qc_filepath = f"/work/reports/catreport/reports/{report_samtools_qc_guid}.json"
        logging.warning(report_samtools_qc_filepath)

        with open(report_samtools_qc_filepath) as f:
            report_samtools_qc_data['tsv'] = f.read()
        report_samtools_qc_data['finished_epochtime'] = int(r[5])
    '''
    end samtools qc report
    '''

    '''
    begin nfnvm nanostats qc report
    '''
    r = get_report_for_type(pipeline_run_uuid, sample_name, 'nfnvm_nanostats_qc')
    print(r)
    report_nfnvm_nanostats_qc_data = dict()
    if r:
        report_nfnvm_nanostats_qc_guid = r[0]
        report_nfnvm_nanostats_qc_filepath = f"/work/reports/catreport/reports/{report_nfnvm_nanostats_qc_guid}.json"
        logging.warning(report_nfnvm_nanostats_qc_filepath)

        with open(report_nfnvm_nanostats_qc_filepath) as f:
            report_nfnvm_nanostats_qc_data['txt'] = f.read()
        report_nfnvm_nanostats_qc_data['finished_epochtime'] = int(r[5])
    '''
    end nfnvm nanostats qc report
    '''

    '''
    begin nfnvm flureport report
    '''
    r = get_report_for_type(pipeline_run_uuid, sample_name, 'nfnvm_flureport')
    print(r)
    report_nfnvm_flureport_data = dict()
    if r:
        report_nfnvm_flureport_guid = r[0]
        report_nfnvm_flureport_filepath = f"/work/reports/catreport/reports/{report_nfnvm_flureport_guid}.json"
        logging.warning(report_nfnvm_flureport_filepath)

        with open(report_nfnvm_flureport_filepath) as f:
            report_nfnvm_flureport_data['txt'] = f.read()
        report_nfnvm_flureport_data['finished_epochtime'] = int(r[5])
    '''
    end nfnvm flureport report
    '''

    '''
    begin nfnvm viralreport report
    '''
    r = get_report_for_type(pipeline_run_uuid, sample_name, 'nfnvm_viralreport')
    print(r)
    report_nfnvm_viralreport_data = dict()
    if r:
        report_nfnvm_viralreport_guid = r[0]
        report_nfnvm_viralreport_filepath = f"/work/reports/catreport/reports/{report_nfnvm_viralreport_guid}.json"
        logging.warning(report_nfnvm_viralreport_filepath)

        with open(report_nfnvm_viralreport_filepath) as f:
            report_nfnvm_viralreport_data['txt'] = f.read()
        report_nfnvm_viralreport_data['finished_epochtime'] = int(r[5])
    '''
    end nfnvm viralreport report
    '''

    print(report_nfnvm_nanostats_qc_data)
    
    return json.dumps({ 'main': { 'sample_name': sample_name,
                                  'pipeline_run_uuid': pipeline_run_uuid, },
                        'samtools_qc': report_samtools_qc_data,
                        'kraken2_speciation': report_kraken2_speciation_data,
                        'mykrobe_speciation': report_mykrobe_speciation_data,
                        'pick_reference': report_pick_reference_data,
                        'resistance': report_resistance_data,
                        'relatedness': dict(),
                        'nfnvm_nanostats_qc': report_nfnvm_nanostats_qc_data,
                        'nfnvm_flureport': report_nfnvm_flureport_data,
                        'nfnvm_viralreport': report_nfnvm_viralreport_data
    })

def main():
    threading.Thread(target=resistance_thread, args=(con,)).start()
    threading.Thread(target=mykrobe_speciation_thread, args=(con,)).start()
    threading.Thread(target=kraken2_speciation_thread, args=(con,)).start()
    threading.Thread(target=pick_reference_thread, args=(con,)).start()
    threading.Thread(target=samtools_qc_thread, args=(con,)).start()
    threading.Thread(target=nfnvm_nanostats_qc_thread, args=(con,)).start()
    threading.Thread(target=nfnvm_flureport_thread, args=(con,)).start()
    threading.Thread(target=nfnvm_viralreport_thread, args=(con,)).start()

    app.run(port=10000)

if __name__ == '__main__':
    main()
