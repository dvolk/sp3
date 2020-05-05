#!/usr/bin/python3.6

import glob
import json
import sys
import pathlib
import requests

data = json.loads(sys.argv[1])

pipeline_run_uuid = data['run_uuid']
pipeline_output_dir = data['output_dir']

files = pathlib.Path(pipeline_output_dir).glob('fluResist_Out/*.fluResistance')

for sample_filepath in files:
    try:
        sample_name_extended = str(sample_filepath.name).replace(".fluResistance", "")
        sample_name = sample_name_extended.split('.')[0]
        p = { 'pipeline_run_uuid': pipeline_run_uuid,
              'sample_name': sample_name_extended,
              'sample_filepath': str(sample_filepath),
              'report_type': 'nfnvm_resistance' }
        print(p)
    
        r = requests.post('http://localhost:10000/req_report/', json = p)
    except Exception as e:
        print(e)
