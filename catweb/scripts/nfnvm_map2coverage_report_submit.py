#!/usr/bin/python3.6

import glob
import json
import pathlib
import sys

import requests

data = json.loads(sys.argv[1])

pipeline_run_uuid = data["run_uuid"]
pipeline_output_dir = data["output_dir"]

files = pathlib.Path(pipeline_output_dir).glob("mapping2_Out/*_cov.png")

for sample_filepath in files:
    try:
        file_name = str(sample_filepath.name).replace("_cov.png", "")
        print("filename:" + file_name)
        index = file_name.rfind("_")
        print("index")
        print(index)
        sample_name = file_name[0:index]
        print("samplename:" + sample_name)

        p = {
            "pipeline_run_uuid": pipeline_run_uuid,
            "sample_name": file_name,
            "sample_filepath": str(sample_filepath),
            "report_type": "nfnvm_map2coverage_report",
        }
        print(p)

        r = requests.post("http://localhost:10000/req_report/", json=p)
    except Exception as e:
        print(e)
