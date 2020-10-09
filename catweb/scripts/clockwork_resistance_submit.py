#!/usr/bin/python3.6

import glob
import json
import sys
import pathlib
import requests

data = json.loads(sys.argv[1])

pipeline_run_uuid = data['run_uuid']
pipeline_output_dir = data['output_dir']

files = list(pathlib.Path(pipeline_output_dir).glob('*/minos/final.vcf'))

print(f"found {len(files)} files")

for sample_filepath in files:
    try:
        sample_name = sample_filepath.parts[-3]
        pipeline_run_uuid = sample_filepath.parts[-4]

        with open(pathlib.Path(pipeline_output_dir) / sample_name / 'speciation' / 'reference_info.txt') as f:
            reference_info = json.loads(f.read())

        p = { 'pipeline_run_uuid': pipeline_run_uuid,
              'sample_name': sample_name,
              'sample_filepath': str(sample_filepath),
              'report_type': 'resistance' }
        print(p)

        if reference_info['pick_taxid'] != "NC_000962.3":
            print(f"skipping {sample_name} (wrong reference)")
            continue

        r = requests.post('http://localhost:10000/req_report/', json = p)
    except Exception as e:
        print(e)
