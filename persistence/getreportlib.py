import resistance_help
import logging
import json
import sqlite3

cons = dict()

def get_samples_cov_names(con, pipeline_run_uuid, sample_name, report_type):
    sample_like = sample_name + '%'

    sql = f'select sample_name from q where status = "done" and pipeline_run_uuid = "{pipeline_run_uuid}" and sample_name like "{sample_like}" and type = "{report_type}" order by added_epochtime desc'

    logging.warning(sql)

    with con:
        r = con.execute(sql).fetchall()
    if r:
        logging.warning(r)
        return r
    else:
        return None

def get_report(cluster_instance_uuid, con, pipeline_run_uuid, sample_name):
    '''
    Get a report (all reports combined) for 1 sample
    '''

    def get_report_for_type(con, pipeline_run_uuid, sample_name, report_type):
        with con:
            r = con.execute('select * from q where status = "done" and pipeline_run_uuid = ? and sample_name = ? and type = ? order by added_epochtime desc',
                            (pipeline_run_uuid, sample_name, report_type)).fetchall()
            logging.warning(r)
        if r:
            return r[0]
        else:
            return None

    if cluster_instance_uuid:
        global cons
        if cluster_instance_uuid in cons:
            con = cons[cluster_instance_uuid]
        else:
            con = sqlite3.connect(f'/work/persistence/{ cluster_instance_uuid }/db/catreport.sqlite', check_same_thread=False)
            cons[cluster_instance_uuid] = con
        reports_directory = f'/work/persistence/{ cluster_instance_uuid }/work/reports/catreport/reports'
    else:
        reports_directory = f'/work/reports/catreport/reports'

    logging.warning(str(cons))
    report_data = dict()

    '''
    begin resistance report
    '''
    r = get_report_for_type(con, pipeline_run_uuid, sample_name, 'resistance')
    report_data['resistance'] = dict()
    if r:
        report_resistance_guid = r[0]
        report_resistance_filepath = f"{ reports_directory }/{report_resistance_guid}.json"
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
    r = get_report_for_type(con, pipeline_run_uuid, sample_name, 'mykrobe_speciation')
    report_data['mykrobe_speciation'] = dict()
    if r:
        report_mykrobe_speciation_guid = r[0]
        report_mykrobe_speciation_filepath = f"{ reports_directory }/{report_mykrobe_speciation_guid}.json"
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
    r = get_report_for_type(con, pipeline_run_uuid, sample_name, 'kraken2_speciation')
    report_data['kraken2_speciation'] = dict()
    if r:
        report_kraken2_speciation_guid = r[0]
        report_kraken2_speciation_filepath = f"{ reports_directory }/{report_kraken2_speciation_guid}.json"
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
    r = get_report_for_type(con, pipeline_run_uuid, sample_name, 'pick_reference')
    report_data['pick_reference'] = dict()
    if r:
        report_pick_reference_guid = r[0]
        report_pick_reference_filepath = f"{ reports_directory }/{report_pick_reference_guid}.json"
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
    r = get_report_for_type(con, pipeline_run_uuid, sample_name, 'samtools_qc')
    report_data['samtools_qc'] = dict()
    if r:
        report_samtools_qc_guid = r[0]
        report_samtools_qc_filepath = f"{ reports_directory }/{report_samtools_qc_guid}.json"
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
    r = get_report_for_type(con, pipeline_run_uuid, sample_name, 'nfnvm_nanostats_qc')
    if r:
        report_data['nfnvm_nanostats_qc'] = dict()
        report_nfnvm_nanostats_qc_guid = r[0]
        report_nfnvm_nanostats_qc_filepath = f"{ reports_directory }/{report_nfnvm_nanostats_qc_guid}.json"
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
    r = get_report_for_type(con, pipeline_run_uuid, sample_name, 'nfnvm_kronareport')

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
    samples_cov_names = get_samples_cov_names(con, pipeline_run_uuid, sample_name, 'nfnvm_map2coverage_report')

    if samples_cov_names != None:
        logging.warning(len(samples_cov_names))
        report_data['nfnvm_map2coverage_report'] = dict()
        report_data['nfnvm_map2coverage_report']['data'] = []
        for sample_cov_name_string in samples_cov_names:
            sample_cov_name = sample_cov_name_string[0]
            logging.warning(sample_cov_name)
            r = get_report_for_type(con, pipeline_run_uuid, sample_cov_name, 'nfnvm_map2coverage_report')

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
    r = get_report_for_type(con, pipeline_run_uuid, sample_name, 'nfnvm_flureport')

    if r:
        report_data['nfnvm_flureport'] = dict()
        report_nfnvm_flureport_guid = r[0]
        report_nfnvm_flureport_filepath = f"{ reports_directory }/{report_nfnvm_flureport_guid}.json"
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
    r = get_report_for_type(con, pipeline_run_uuid, sample_name, 'nfnvm_viralreport')

    if r:
        report_data['nfnvm_viralreport'] = dict()
        report_nfnvm_viralreport_guid = r[0]
        report_nfnvm_viralreport_filepath = f"{ reports_directory }/{report_nfnvm_viralreport_guid}.json"
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
    samples_resistance_names = get_samples_cov_names(con, pipeline_run_uuid, sample_name, 'nfnvm_resistance')

    if samples_resistance_names != None:
        logging.warning(len(samples_cov_names))
        report_data['nfnvm_resistance_report'] = dict()
        report_data['nfnvm_resistance_report']['data'] = []
        for sample_resistance_name_string in samples_resistance_names:
            sample_resistance_name = sample_resistance_name_string[0]
            logging.warning(sample_resistance_name)
            r = get_report_for_type(con, pipeline_run_uuid, sample_resistance_name, 'nfnvm_resistance')

            sample_ref_files = dict()

            if r:
                report_nfnvm_resistance_guid = r[0]
                report_nfnvm_resistance_downloadpath = f"{ reports_directory }/{ report_nfnvm_resistance_guid }"
                logging.warning(report_nfnvm_resistance_downloadpath)
                sample_ref_files['name'] = sample_resistance_name
                sample_ref_files['path'] = report_nfnvm_resistance_downloadpath
                logging.warning(report_nfnvm_resistance_downloadpath)
                report_data['nfnvm_resistance_report']['finished_epochtime'] =  int(r[5])
                with open(report_nfnvm_resistance_downloadpath) as f:
                    resistance = dict()
                    resistance['species'] = sample_resistance_name
                    resistance['drug'] = []
                    logging.warning(f"resistance species: {resistance['species']}")
                    content_in_file = f.read()
                    for row in content_in_file.split('\n'):
                        resistance['drug'].append(row.split('\t'))
                        logging.warning(f"resistance drug: {resistance['drug']}")
                    report_data['nfnvm_resistance_report']['data'].append(resistance)
    '''
    end nfnvm resistance report
    '''
    
    return { 'status': 'success', 'details': None, 'data': { 'report_data': report_data }}
