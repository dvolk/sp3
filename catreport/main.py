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

def db_insert_new(new_row):
    with sql_lock, con:
        con.execute('insert into q values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', new_row)

def db_get_report_for_type(pipeline_run_uuid, sample_name, report_type):
    with sql_lock, con:
        r = con.execute('select * from q where status = "done" and pipeline_run_uuid = ? and sample_name = ? and type = ? order by added_epochtime desc',
                        (pipeline_run_uuid, sample_name, report_type)).fetchall()
    if r:
        return r[0]
    else:
        return None

def get_samples_cov_names(pipeline_run_uuid, sample_name, report_type):

    sample_like = sample_name + '%'

    sql = f'select sample_name from q where status = "done" and pipeline_run_uuid = "{pipeline_run_uuid}" and sample_name like "{sample_like}" and type = "{report_type}" order by added_epochtime desc'

    logging.warning(sql)

    with sql_lock, con:
        r = con.execute(sql).fetchall()
    if r:
        logging.warning(r)
        return r
    else:
        return None

def db_get_queue(con, report_type):
    with sql_lock, con:
        rows = con.execute("select * from q where status = 'queued' and type = ? order by added_epochtime asc limit 1", (report_type,)).fetchall()
    return rows

def db_update_report_result(con, report_filename, report_started_epochtime, report_finished_epochtime, report_status, report_uuid):
    with sql_lock, con:
        con.execute("update q set report_filename = ?, started_epochtime = ?, finished_epochtime = ?, status = ? where uuid = ?",
                    (report_filename, report_started_epochtime, report_finished_epochtime, report_status, report_uuid ))

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
    db_insert_new(new_row)

    return "queued"

def report_thread_factory(con, report_type, make_report_function):
    print(f"starting thread for {report_type}")
    while True:
        rows = db_get_queue(con, report_type)
        if rows:
            row = rows[0]
            report_uuid = row[0]
            sample_filepath = row[8]
            sample_name = row[7]
            pipeline_run_uuid = row[6]

            report_started_epochtime = epochtime()
            print(f"{report_type}_thread: working on {report_uuid} ({sample_filepath})")
            report_filename = make_report_function(report_uuid, sample_filepath, sample_name, pipeline_run_uuid)
            print(f"{report_type}_thread: finished with {report_uuid}")
            report_status = 'done'
            report_finished_epochtime = epochtime()
            db_update_report_result(con, report_filename, report_started_epochtime, report_finished_epochtime, report_status, report_uuid)

        time.sleep(1)

def get_report_for_type(pipeline_run_uuid, sample_name, report_type):
    '''
    Query database for report

    Mandatory inputs: pipeline run uuid, sample name, report type
    '''
    return db_get_report_for_type(pipeline_run_uuid, sample_name, report_type)

def make_resistance_report(report_uuid, sample_filepath, sample_name, pipeline_run_uuid):
    '''
    1. symlink sample file path to /work/reports/resistanceapi/vcfs/{report_uuid}.vcf
    2. send request for report to resistance api
    3. write report to /work/reports/catreport/reports/{report_uuid}.json
    4. delete symlink from 1.
    '''
    os.system(f'cd /work/reports/resistanceapi/vcfs; ln -s {sample_filepath} {report_uuid}.vcf')
    url = f'http://localhost:8990/api/v1/resistances/piezo/{report_uuid}?type=piezo'
    logging.warning('res api')
    r = requests.get(url)
    logging.warning('res api end')
    try:
        out_filepath = f'/work/reports/catreport/reports/{report_uuid}.json'
        with open(out_filepath, 'w') as report_file:
            report_file.write(r.text)
        os.system(f'cd /work/reports/resistanceapi/vcfs && rm {report_uuid}.vcf')

    except Exception as e:
        logging.warning("couldn't write report file")
        logging.warning(str(e))

    return out_filepath

def make_trivial_copy_report(report_uuid, sample_filepath, sample_name, pipeline_run_uuid):
    out_filepath = f'/work/reports/catreport/reports/{report_uuid}.json'
    os.system(f'cp {sample_filepath} {out_filepath}')
    return out_filepath

def make_file_copy_report(report_file_path, sample_filepath, sample_name, pipeline_run_uuid):
    out_filepath = f'/work/reports/catreport/reports/{report_file_path}'
    os.system(f'cp {sample_filepath} {out_filepath}')
    return out_filepath

@app.route('/report/<pipeline_run_uuid>/<sample_name>')
def get_report(pipeline_run_uuid, sample_name):
    '''
    Get a report (all reports combined) for 1 sample
    '''

    report_data = dict()

    '''
    begin resistance report
    '''
    r = get_report_for_type(pipeline_run_uuid, sample_name, 'resistance')
    report_data['resistance'] = dict()
    if r:
        report_resistance_guid = r[0]
        report_resistance_filepath = f"/work/reports/catreport/reports/{report_resistance_guid}.json"
        logging.warning(report_resistance_filepath)
        try:
            with open(report_resistance_filepath) as f:
                report_data['resistance']['data'] = json.loads(f.read())['data']
            report_data['resistance']['finished_epochtime'] = int(r[5])
            report_data['resistance']['data'] = resistance_help.resistance_postprocess(report_data)

        except Exception as e:
            logging.error("resistance report processing failed")
            logging.error(str(e))
            report_data['resistance'] = dict()

    '''
    end resistance report
    '''

    '''
    begin speciation report
    '''
    r = get_report_for_type(pipeline_run_uuid, sample_name, 'mykrobe_speciation')
    report_data['mykrobe_speciation'] = dict()
    if r:
        report_mykrobe_speciation_guid = r[0]
        report_mykrobe_speciation_filepath = f"/work/reports/catreport/reports/{report_mykrobe_speciation_guid}.json"
        logging.warning(report_mykrobe_speciation_filepath)

        with open(report_mykrobe_speciation_filepath) as f:
            report_data['mykrobe_speciation']['data'] = json.loads(f.read())
        report_data['mykrobe_speciation']['finished_epochtime'] = int(r[5])
    '''
    end speciation report
    '''

    '''
    begin speciation report
    '''
    r = get_report_for_type(pipeline_run_uuid, sample_name, 'kraken2_speciation')
    report_data['kraken2_speciation'] = dict()
    if r:
        report_kraken2_speciation_guid = r[0]
        report_kraken2_speciation_filepath = f"/work/reports/catreport/reports/{report_kraken2_speciation_guid}.json"
        logging.warning(report_kraken2_speciation_filepath)

        with open(report_kraken2_speciation_filepath) as f:
            report_data['kraken2_speciation']['data'] = f.read()
        report_data['kraken2_speciation']['finished_epochtime'] = int(r[5])
    '''
    end speciation report
    '''

    '''
    begin pick reference report
    '''
    r = get_report_for_type(pipeline_run_uuid, sample_name, 'pick_reference')
    report_data['pick_reference'] = dict()
    if r:
        report_pick_reference_guid = r[0]
        report_pick_reference_filepath = f"/work/reports/catreport/reports/{report_pick_reference_guid}.json"
        logging.warning(report_pick_reference_filepath)

        with open(report_pick_reference_filepath) as f:
            report_data['pick_reference']['data'] = json.loads(f.read())
        report_data['pick_reference']['finished_epochtime'] = int(r[5])
    '''
    end speciation report
    '''

    '''
    begin samtools qc report
    '''
    r = get_report_for_type(pipeline_run_uuid, sample_name, 'samtools_qc')
    report_data['samtools_qc'] = dict()
    if r:
        report_samtools_qc_guid = r[0]
        report_samtools_qc_filepath = f"/work/reports/catreport/reports/{report_samtools_qc_guid}.json"
        logging.warning(report_samtools_qc_filepath)

        with open(report_samtools_qc_filepath) as f:
            report_data['samtools_qc']['data'] = f.read()
        report_data['samtools_qc']['finished_epochtime'] = int(r[5])
    '''
    end samtools qc report
    '''

    '''
    begin nfnvm nanostats qc report
    '''
    r = get_report_for_type(pipeline_run_uuid, sample_name, 'nfnvm_nanostats_qc')
    if r:
        report_data['nfnvm_nanostats_qc'] = dict()
        report_nfnvm_nanostats_qc_guid = r[0]
        report_nfnvm_nanostats_qc_filepath = f"/work/reports/catreport/reports/{report_nfnvm_nanostats_qc_guid}.json"
        logging.warning(report_nfnvm_nanostats_qc_filepath)

        with open(report_nfnvm_nanostats_qc_filepath) as f:
            report_data['nfnvm_nanostats_qc']['data'] = f.read()
        report_data['nfnvm_nanostats_qc']['finished_epochtime'] = int(r[5])
    '''
    end nfnvm nanostats qc report
    '''

    '''
    begin nfnvm krona report
    '''
    r = get_report_for_type(pipeline_run_uuid, sample_name, 'nfnvm_kronareport')

    if r:
        report_data['nfnvm_kronareport'] = dict()
        report_nfnvm_krona_html = r[0]
        report_nfnvm_krona_downloadpath = f"{pipeline_run_uuid}/selReference_Out/{sample_name}_classkrona.html"
        logging.warning(report_nfnvm_krona_downloadpath)

        report_data['nfnvm_kronareport']['path'] = report_nfnvm_krona_downloadpath
        report_data['nfnvm_kronareport']['finished_epochtime'] = int(r[5])
    '''
    end nfnvm krona report
    '''

    '''
    begin nfnvm map2coverage report
    '''
    samples_cov_names = get_samples_cov_names(pipeline_run_uuid, sample_name, 'nfnvm_map2coverage_report')

    if samples_cov_names != None:
        logging.warning(len(samples_cov_names))
        report_data['nfnvm_map2coverage_report'] = dict()
        report_data['nfnvm_map2coverage_report']['data'] = []
        for sample_cov_name_string in samples_cov_names:
            sample_cov_name = sample_cov_name_string[0]
            logging.warning(sample_cov_name)
            r = get_report_for_type(pipeline_run_uuid, sample_cov_name, 'nfnvm_map2coverage_report')

            sample_ref_files = dict()

            if r:
                #efd531dd-1c9c-4ece-af1e-e33ee5252b35/mapping2_Out/F10_BC01_MK077344_cov.png
                report_nfnvm_cov_downloadpath = f"{pipeline_run_uuid}/mapping2_Out/{sample_cov_name}_cov.png"
                logging.warning(report_nfnvm_cov_downloadpath)
                sample_ref_files['name'] = sample_cov_name
                sample_ref_files['path'] = report_nfnvm_cov_downloadpath
                report_data['nfnvm_map2coverage_report']['finished_epochtime'] =  int(r[5])
                report_data['nfnvm_map2coverage_report']['data'].append(sample_ref_files)
                logging.warning(report_nfnvm_cov_downloadpath)

    '''
    end nfnvm map2coverage report
    '''

    '''
    begin nfnvm flureport report
    '''
    r = get_report_for_type(pipeline_run_uuid, sample_name, 'nfnvm_flureport')

    if r:
        report_data['nfnvm_flureport'] = dict()
        report_nfnvm_flureport_guid = r[0]
        report_nfnvm_flureport_filepath = f"/work/reports/catreport/reports/{report_nfnvm_flureport_guid}.json"
        logging.warning(report_nfnvm_flureport_filepath)

        with open(report_nfnvm_flureport_filepath) as f:
            report_data['nfnvm_flureport']['data'] = f.read()
        report_data['nfnvm_flureport']['finished_epochtime'] = int(r[5])
    '''
    end nfnvm flureport report
    '''

    '''
    begin nfnvm viralreport report
    '''
    r = get_report_for_type(pipeline_run_uuid, sample_name, 'nfnvm_viralreport')

    if r:
        report_data['nfnvm_viralreport'] = dict()
        report_nfnvm_viralreport_guid = r[0]
        report_nfnvm_viralreport_filepath = f"/work/reports/catreport/reports/{report_nfnvm_viralreport_guid}.json"
        logging.warning(report_nfnvm_viralreport_filepath)

        with open(report_nfnvm_viralreport_filepath) as f:
            report_data['nfnvm_viralreport']['data'] = f.read()
        report_data['nfnvm_viralreport']['finished_epochtime'] = int(r[5])
    '''
    end nfnvm viralreport report
    '''

    '''
    begin nfnvm resistance report
    '''
    samples_resistance_names = get_samples_cov_names(pipeline_run_uuid, sample_name, 'nfnvm_resistance')

    if samples_resistance_names != None:
        logging.warning(len(samples_cov_names))
        report_data['nfnvm_resistance_report'] = dict()
        report_data['nfnvm_resistance_report']['data'] = []
        for sample_resistance_name_string in samples_resistance_names:
            sample_resistance_name = sample_resistance_name_string[0]
            logging.warning(sample_resistance_name)
            r = get_report_for_type(pipeline_run_uuid, sample_resistance_name, 'nfnvm_resistance')

            sample_ref_files = dict()

            if r:
                report_nfnvm_resistance_guid = r[0]
                #efd531dd-1c9c-4ece-af1e-e33ee5252b35/fluResist_Out/A2_REF_MK576859.fluResistance
                report_nfnvm_resistance_downloadpath = f"/work/reports/catreport/reports/{ report_nfnvm_resistance_guid }"
                logging.warning(report_nfnvm_resistance_downloadpath)
                sample_ref_files['name'] = sample_resistance_name
                sample_ref_files['path'] = report_nfnvm_resistance_downloadpath
                logging.warning(report_nfnvm_resistance_downloadpath)
                report_data['nfnvm_resistance_report']['finished_epochtime'] =  int(r[5])
                with open(report_nfnvm_resistance_downloadpath) as f:
                    data_in_resistance_file = f.read()
                    logging.warning(f"data_in_resistance_file: {data_in_resistance_file}")
                    report_data['nfnvm_resistance_report']['data'].append(data_in_resistance_file)
                logging.warning(report_nfnvm_resistance_downloadpath)
    '''
    end nfnvm resistance report
    '''

    
    return json.dumps({ 'status': 'success', 'details': None, 'data': { 'report_data': report_data }})

def main():

    threading.Thread(target=report_thread_factory, args=(con, "resistance", make_resistance_report)).start()
    threading.Thread(target=report_thread_factory, args=(con, "mykrobe_speciation", make_trivial_copy_report)).start()
    threading.Thread(target=report_thread_factory, args=(con, "kraken2_speciation", make_trivial_copy_report)).start()
    threading.Thread(target=report_thread_factory, args=(con, "pick_reference", make_trivial_copy_report)).start()
    threading.Thread(target=report_thread_factory, args=(con, "samtools_qc", make_trivial_copy_report)).start()

    threading.Thread(target=report_thread_factory, args=(con, "nfnvm_nanostats_qc", make_trivial_copy_report)).start()
    threading.Thread(target=report_thread_factory, args=(con, "nfnvm_kronareport", make_file_copy_report)).start()
    threading.Thread(target=report_thread_factory, args=(con, "nfnvm_flureport", make_trivial_copy_report)).start()
    threading.Thread(target=report_thread_factory, args=(con, "nfnvm_viralreport", make_trivial_copy_report)).start()
    threading.Thread(target=report_thread_factory, args=(con, "nfnvm_map2coverage_report", make_file_copy_report)).start()

    threading.Thread(target=report_thread_factory, args=(con, "nfnvm_resistance", make_file_copy_report)).start()

    app.run(port=10000)

if __name__ == '__main__':
    main()
