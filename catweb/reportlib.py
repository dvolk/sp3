import logging
import json
import time
import pandas

from io import StringIO

def process_reports(report_data, catpile_resp, download_url):
    template_report_data = dict() # data out to template

    if catpile_resp:
        template_report_data['catpile_metadata'] = dict()
        template_report_data['catpile_metadata']['data'] = catpile_resp

    if 'samtools_qc' in report_data.keys() and 'data' in report_data['samtools_qc']:
        template_report_data['samtools_qc'] = dict()
        template_report_data['samtools_qc']['data'] = dict()
        for line in report_data['samtools_qc']['data'].split('\n'):
            elems = line.split('\t')
            if elems[0] == 'SN':
                template_report_data['samtools_qc']['data'][elems[1]] = elems[2]
        template_report_data['samtools_qc']['finished_epochtime'] = time.strftime("%Y/%m/%d %H:%M", time.localtime(report_data['samtools_qc']['finished_epochtime']))

    if 'nfnvm_nanostats_qc' in report_data.keys() and 'data' in report_data['nfnvm_nanostats_qc']:
        template_report_data['nfnvm_nanostats_qc'] = dict()
        template_report_data['nfnvm_nanostats_qc']['data'] = dict()
        for line in report_data['nfnvm_nanostats_qc']['data'].split('\n')[1:8]:
            elems = line.split(':')
            template_report_data['nfnvm_nanostats_qc']['data'][elems[0].strip()] = elems[1].strip()
        template_report_data['nfnvm_nanostats_qc']['finished_epochtime'] = time.strftime("%Y/%m/%d %H:%M", time.localtime(report_data['nfnvm_nanostats_qc']['finished_epochtime']))

    if 'nfnvm_kronareport' in report_data.keys() and 'data' in report_data['nfnvm_kronareport']:
        template_report_data['nfnvm_kronareport'] = dict()
        template_report_data['nfnvm_kronareport']['download_url'] = download_url +  report_data['nfnvm_kronareport']['path']
        template_report_data['nfnvm_kronareport']['finished_epochtime'] = time.strftime("%Y/%m/%d %H:%M", time.localtime(report_data['nfnvm_kronareport']['finished_epochtime']))

    if 'nfnvm_map2coverage_report' in report_data.keys() and 'data' in report_data['nfnvm_map2coverage_report']:
        template_report_data['nfnvm_map2coverage_report'] = dict()
        template_report_data['nfnvm_map2coverage_report']['data'] = report_data['nfnvm_map2coverage_report']['data']
        template_report_data['nfnvm_map2coverage_report']['download_url'] = download_url
        template_report_data['nfnvm_map2coverage_report']['finished_epochtime'] = time.strftime("%Y/%m/%d %H:%M", time.localtime(report_data['nfnvm_map2coverage_report']['finished_epochtime']))

    if 'nfnvm_resistance_report' in report_data.keys() and 'data' in report_data['nfnvm_resistance_report']:
        template_report_data['nfnvm_resistance_report'] = dict()
        template_report_data['nfnvm_resistance_report']['data'] = report_data['nfnvm_resistance_report']['data']
        template_report_data['nfnvm_resistance_report']['data'] = list()

        for resistance in report_data['nfnvm_resistance_report']['data']:
            if resistance:
                logging.error(f"resistance: {resistance}")
                template_report_data['nfnvm_resistance_report']['data'].append(resistance)

        template_report_data['nfnvm_resistance_report']['finished_epochtime'] = time.strftime("%Y/%m/%d %H:%M", time.localtime(report_data['nfnvm_resistance_report']['finished_epochtime']))

    if 'nfnvm_flureport' in report_data.keys():
        template_report_data['nfnvm_flureport'] = dict()
        template_report_data['nfnvm_flureport']['data'] = dict()
        [line1, line2, _] = report_data['nfnvm_flureport']['data'].split('\n')
        line1 = line1.split('\t')
        line2 = line2.split('\t')
        for i in range(0, 7):
            template_report_data['nfnvm_flureport']['data'][line1[i]] = line2[i]
        template_report_data['nfnvm_flureport']['finished_epochtime'] = time.strftime("%Y/%m/%d %H:%M", time.localtime(report_data['nfnvm_flureport']['finished_epochtime']))

    if 'nfnvm_viralreport' in report_data.keys() and 'data' in report_data['nfnvm_viralreport']:
        template_report_data['nfnvm_viralreport'] = dict()
        template_report_data['nfnvm_viralreport']['data'] = list()
        header = report_data['nfnvm_viralreport']['data'].split('\n')[0]
        template_report_data['nfnvm_viralreport']['head'] = header.split('\t')
        logging.warning(header)
        for line in report_data['nfnvm_viralreport']['data'].split('\n')[1:]:
            elems = line.split('\t')
            template_report_data['nfnvm_viralreport']['data'].append(elems)
        template_report_data['nfnvm_viralreport']['finished_epochtime'] = time.strftime("%Y/%m/%d %H:%M", time.localtime(report_data['nfnvm_flureport']['finished_epochtime']))

    if 'pick_reference' in report_data and 'data' in report_data['pick_reference']:
        template_report_data['pick_reference'] = dict()
        template_report_data['pick_reference']['data'] = report_data['pick_reference']['data']
        template_report_data['pick_reference']['finished_epochtime'] = time.strftime("%Y/%m/%d %H:%M", time.localtime(report_data['pick_reference']['finished_epochtime']))

    if 'resistance' in report_data and 'data' in report_data['resistance']:
        template_report_data['resistance'] = dict()
        template_report_data['resistance']['data'] = report_data['resistance']['data']
        template_report_data['resistance']['raw_data'] = report_data['resistance']['raw_data']
        template_report_data['resistance']['message'] = report_data['resistance']['message']
        template_report_data['resistance']['finished_epochtime'] = time.strftime("%Y/%m/%d %H:%M", time.localtime(report_data['resistance']['finished_epochtime']))
        template_report_data['resistance']['status'] = report_data['resistance']['status']

    if 'mykrobe_speciation' in report_data and 'data' in report_data['mykrobe_speciation']:
        import parse_mykrobe
        input_data = report_data['mykrobe_speciation']['data']
        result = parse_mykrobe.report_species(input_data)
        template_report_data['mykrobe_speciation'] = dict()
        template_report_data['mykrobe_speciation']['data'] = result
        template_report_data['mykrobe_speciation']['finished_epochtime'] = time.strftime("%Y/%m/%d %H:%M", time.localtime(report_data['mykrobe_speciation']['finished_epochtime']))

    if 'kraken2_speciation' in report_data and 'data' in report_data['kraken2_speciation']:
        import parse_kraken2
        pct_threshold = 1
        num_threshold = 10000
        input_data = report_data['kraken2_speciation']['data']
        result = parse_kraken2.read_kraken2(input_data, pct_threshold, num_threshold)
        sorted_result = parse_kraken2.sort_result(result, pct_threshold, num_threshold)

        template_report_data['kraken2_speciation'] = dict()
        template_report_data['kraken2_speciation']['data'] = dict()
        template_report_data['kraken2_speciation']['data']['Family'] = sorted_result['Family']
        template_report_data['kraken2_speciation']['data']['Genus'] = sorted_result['Genus']
        template_report_data['kraken2_speciation']['data']['Species complex'] = sorted_result['Species complex']
        template_report_data['kraken2_speciation']['data']['Species'] = sorted_result['Species']
        template_report_data['kraken2_speciation']['data']['Warnings'] = sorted_result['Warnings']
        # format report time
        template_report_data['kraken2_speciation']['finished_epochtime'] = time.strftime("%Y/%m/%d %H:%M", time.localtime(report_data['kraken2_speciation']['finished_epochtime']))

    return template_report_data
