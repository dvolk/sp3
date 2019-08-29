#!/usr/bin/python3.6

import glob
import json
import sys
import pathlib
import requests

data = json.loads(sys.argv[1])

pipeline_run_uuid = data['run_uuid']
pipeline_output_dir = data['output_dir']

files = pathlib.Path(pipeline_output_dir).glob('*/*/*_kraken2.tab')

for sample_filepath in files:
    # >>> p = list(pathlib.Path.cwd().glob('*/*/final.vcf'))[0]
    # >>> p.parts
    # ('/', 'mnt', 'disk2', 'output', 'abf01c96-19f8-48ec-b162-fb9710d49872', 'ERR2509678', 'minos', 'final.vcf')
    try:
        sample_name = sample_filepath.parts[-3]
        pipeline_run_uuid = sample_filepath.parts[-4]
        
        p = { 'pipeline_run_uuid': pipeline_run_uuid,
              'sample_name': sample_name,
              'sample_filepath': str(sample_filepath),
              'report_type': 'kraken2_speciation' }
        print(p)
    
        r = requests.post('http://localhost:10000/req_report/', json = p)
    except:
        pass
