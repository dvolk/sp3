import resistance_help
import datetime
import logging
import json

def get_samples_cov_names(reports_db, pipeline_run_uuid, sample_name, report_type):
    logging.warning(f"reports_db: {reports_db}")
    logging.warning(f"pipeline_run_uuid: {pipeline_run_uuid}")
    logging.warning(f"sample_name: {sample_name}")
    logging.warning(f"report_type: {report_type}")

    return reports_db.find({ "sample_name": f"sample_name.*",
                             "status": "done",
                             "pipeline_run_uuid": pipeline_run_uuid,
                             "type": report_type }, { "sample_name": 1 }, sort=[("added_epochtime", 1)])

def get_report(reports_db, fs, pipeline_run_uuid, sample_name):
    a = datetime.datetime.now()
    '''
    Get a report (all reports combined) for 1 sample
    '''
    def get_report_file(report_uuid):
        r = fs.find_one({ "filename": report_uuid }).read()
        if not r:
            logging.warning(f"gridfs file {report_uuid} for run {pipeline_run_uuid} sample {sample_name} not found or empty")
            return None
        try:
            return r.decode()
        except:
            return r
        return r

    def get_report_for_type(pipeline_run_uuid, sample_name, report_type):
        r = reports_db.find_one({ "status": "done",
                                  "pipeline_run_uuid": pipeline_run_uuid,
                                  "sample_name": sample_name,
                                  "type": report_type }, sort=[("added_epochtime", 1)])

    r_all = list(reports_db.find({ "status": "done",
                                   "pipeline_run_uuid": pipeline_run_uuid,
                                   "sample_name": sample_name }, sort=[("added_epochtime", 1)]))
    r_all = { r['type']:r for r in r_all }

    report_data = dict()

    '''
    begin resistance report
    '''
    r = r_all.get('resistance')
    report_data['resistance'] = dict()
    if r:
        report_resistance_guid = r['uuid']
        try:
            file_content = get_report_file(r['uuid'])
            file_json_content = json.loads(file_content)
            report_data['resistance']['finished_epochtime'] = int(r["finished_epochtime"])
            report_data['resistance']['status'] = 'success'
            report_data['resistance']['message'] = file_json_content['message']
            report_data['resistance']['raw_data'] = file_content
            report_data['resistance']['data'] = file_json_content['data']
            report_data['resistance']['data'] = resistance_help.resistance_postprocess(report_data)
        except Exception as e:
            logging.error("*** resistance report processing failed")
            logging.error(repr(e))
            report_data['resistance']['status'] = 'failure'
            report_data['resistance']['message'] = repr(e)
    '''
    end resistance report
    '''

    '''
    begin speciation report
    '''
    r = r_all.get('mykrobe_speciation')
    report_data['mykrobe_speciation'] = dict()
    if r:
        f = get_report_file(r['uuid'])
        if f:
            report_data['mykrobe_speciation']['data'] = json.loads(f)
            report_data['mykrobe_speciation']['finished_epochtime'] = int(r["finished_epochtime"])
    '''
    end speciation report
    '''

    '''
    begin run distmatrix report
    '''
    r = get_report_for_type(pipeline_run_uuid, '-', 'run_distmatrix')
    report_data['run_distmatrix'] = dict()
    if r:
        report_data['run_distmatrix']['data'] = dict()
        report_data['run_distmatrix']['data']['samples'] = dict()
        j = json.loads(get_report_file(r['uuid']))
        if 'samples' in j and sample_name in j['samples']:
            report_data['run_distmatrix']['data']['samples'][sample_name] = j['samples'][sample_name]
        report_data['run_distmatrix']['finished_epochtime'] = int(r["finished_epochtime"])
    '''
    end run distmatrix report
    '''

    '''
    begin speciation report
    '''
    r = r_all.get('kraken2_speciation')
    report_data['kraken2_speciation'] = dict()
    if r:
        f = get_report_file(r['uuid'])
        if f:
            report_data['kraken2_speciation']['data'] = f
            report_data['kraken2_speciation']['finished_epochtime'] = int(r["finished_epochtime"])
    '''
    end speciation report
    '''

    '''
    begin pick reference report
    '''
    r = r_all.get('pick_reference')
    report_data['pick_reference'] = dict()
    if r:
        f = get_report_file(r['uuid'])
        if f:
            report_data['pick_reference']['data'] = json.loads(f)
            report_data['pick_reference']['finished_epochtime'] = int(r["finished_epochtime"])
    '''
    end speciation report
    '''

    '''
    begin samtools qc report
    '''
    r = r_all.get('samtools_qc')
    report_data['samtools_qc'] = dict()
    if r:
        f = get_report_file(r['uuid'])
        if f:
            report_data['samtools_qc']['data'] = f
            report_data['samtools_qc']['finished_epochtime'] = int(r["finished_epochtime"])
    '''
    end samtools qc report
    '''

    '''
    begin nfnvm nanostats qc report
    '''
    r = r_all.get('nfnvm_nanostats_qc')
    if r:
        report_data['nfnvm_nanostats_qc'] = dict()
        report_data['nfnvm_nanostats_qc']['data'] = get_report_file(r['uuid'])
        report_data['nfnvm_nanostats_qc']['finished_epochtime'] = int(r["finished_epochtime"])
    '''
    end nfnvm nanostats qc report
    '''

    '''
    begin nfnvm krona report
    '''
    r = r_all.get('nfnvm_kronareport')

    if r:
        report_data['nfnvm_kronareport'] = dict()
        report_nfnvm_krona_html = r["uuid"]
        report_nfnvm_krona_downloadpath = f"{pipeline_run_uuid}/selReference_Out/{sample_name}_classkrona.html"
        logging.warning(report_nfnvm_krona_downloadpath)

        report_data['nfnvm_kronareport']['path'] = report_nfnvm_krona_downloadpath
        report_data['nfnvm_kronareport']['finished_epochtime'] = int(r["finished_epochtime"])
    '''
    end nfnvm krona report
    '''

    '''
    begin nfnvm map2coverage report
    '''
    logging.warning(f"Calling get_samples_cov_names with report type: nfnvm_map2coverage_report")
    samples_cov_names = list(get_samples_cov_names(reports_db, pipeline_run_uuid, sample_name, 'nfnvm_map2coverage_report'))
    logging.warning(samples_cov_names)

    if samples_cov_names:
        logging.warning(len(samples_cov_names))
        report_data['nfnvm_map2coverage_report'] = dict()
        report_data['nfnvm_map2coverage_report']['data'] = []
        for sample_cov_name_string in samples_cov_names:
            sample_cov_name = sample_cov_name_string[0]
            logging.warning(sample_cov_name)
            r = get_report_for_type(reports_db, pipeline_run_uuid, sample_cov_name, 'nfnvm_map2coverage_report')

            sample_ref_files = dict()

            if r:
                #efd531dd-1c9c-4ece-af1e-e33ee5252b35/mapping2_Out/F10_BC01_MK077344_cov.png
                report_nfnvm_cov_downloadpath = f"{pipeline_run_uuid}/mapping2_Out/{sample_cov_name}_cov.png"
                logging.warning(report_nfnvm_cov_downloadpath)
                sample_ref_files['name'] = sample_cov_name
                sample_ref_files['path'] = report_nfnvm_cov_downloadpath
                report_data['nfnvm_map2coverage_report']['finished_epochtime'] =  int(r["finished_epochtime"])
                report_data['nfnvm_map2coverage_report']['data'].append(sample_ref_files)
                logging.warning(report_nfnvm_cov_downloadpath)

    '''
    end nfnvm map2coverage report
    '''

    '''
    begin nfnvm flureport report
    '''
    r = r_all.get('nfnvm_flureport')

    if r:
        report_data['nfnvm_flureport'] = dict()
        report_data['nfnvm_flureport']['data'] = get_report_file(r['uuid'])
        report_data['nfnvm_flureport']['finished_epochtime'] = int(r["finished_epochtime"])
    '''
    end nfnvm flureport report
    '''

    '''
    begin nfnvm viralreport report
    '''
    r = r_all.get('nfnvm_viralreport')

    if r:
        report_data['nfnvm_viralreport'] = dict()
        report_data['nfnvm_viralreport']['data'] = get_report_file(r['uuid'])
        report_data['nfnvm_viralreport']['finished_epochtime'] = int(r["finished_epochtime"])
    '''
    end nfnvm viralreport report
    '''

    '''
    begin nfnvm resistance report
    '''
    samples_resistance_names = list(get_samples_cov_names(reports_db, pipeline_run_uuid, sample_name, 'nfnvm_resistance'))

    if samples_resistance_names:
        logging.warning(len(samples_cov_names))
        report_data['nfnvm_resistance_report'] = dict()
        report_data['nfnvm_resistance_report']['data'] = []
        for sample_resistance_name_string in samples_resistance_names:
            sample_resistance_name = sample_resistance_name_string[0]
            logging.warning(sample_resistance_name)
            r = get_report_for_type(pipeline_run_uuid, sample_resistance_name, 'nfnvm_resistance')

            sample_ref_files = dict()

            if r:

                sample_ref_files['name'] = sample_resistance_name
                sample_ref_files['path'] = report_nfnvm_resistance_downloadpath
                report_data['nfnvm_resistance_report']['finished_epochtime'] =  r["finished_epochtime"]
                resistance = dict()
                resistance['species'] = sample_resistance_name
                resistance['drug'] = []
                logging.warning(f"resistance species: {resistance['species']}")
                content_in_file = get_report_file(r['uuid'])
                for row in content_in_file.split('\n'):
                    resistance['drug'].append(row.split('\t'))
                    logging.warning(f"resistance drug: {resistance['drug']}")
                report_data['nfnvm_resistance_report']['data'].append(resistance)
    '''
    end nfnvm resistance report
    '''

    b = datetime.datetime.now()
    logging.warning(f"get_report({pipeline_run_uuid}, {sample_name}) finished in {(b-a).total_seconds()} s")
    return { 'status': 'success', 'details': None, 'data': { 'report_data': report_data }}
