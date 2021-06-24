#!/usr/bin/python3.6

import glob
import json
import pathlib
import sys

import requests

data = json.loads(sys.argv[1])

pipeline_run_uuid = data["run_uuid"]
pipeline_output_dir = data["output_dir"]

p = {
    "pipeline_run_uuid": pipeline_run_uuid,
    "sample_name": "-",
    "sample_filepath": "-",
    "report_type": "run_distmatrix",
}
print(p)

r = requests.post("http://localhost:10000/req_report/", json=p)
