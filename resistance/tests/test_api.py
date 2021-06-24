"""
Test resistance api endpoints and check the json result
To run tests:
1. Start resistance api: python3 resistanceapi/src/main.py
2. Have the test files (vcfs under piezo/examples) ready in /vcfs
3. Run: nosetests tests
4. Or Run: nosetests tests/test_api.py:test_data_response
----------------------------------------------------------
To verify with piezo, run
python3 piezo-vcf-parse.py  \
                      --vcf_file examples/01/01.vcf\
                      --genbank_file config/H37rV_v3.gbk\
                      --catalogue_file config/NEJM2018-RSU-catalogue-H37rV_v3.csv\
                      --catalogue_name NEJM2018
Make sure the resistanceapi/config has configured for above parameters
"""
import json

import requests
from nose.tools import assert_true


def test_data_response():
    url = "http://localhost:8990/api/v1/resistances/data"
    response = requests.get(url)
    assert_true(response.ok)


def test_data_json():
    url = "http://localhost:8990/api/v1/resistances/data"
    response = requests.get(url)
    resulted_data = json.loads(response.text)["data"]
    assert_true("genelist.txt" in resulted_data)
    assert_true("NEJM2018-RSU-catalogue-H37rV_v3.csv" in resulted_data)
    assert_true("H37rV_v3.gbk" in resulted_data)


def test_genelist_response():
    url = "http://localhost:8990/api/v1/resistances/data/genelist.txt"
    response = requests.get(url)
    assert_true(response.ok)


def test_genelist_json():
    url = "http://localhost:8990/api/v1/resistances/data/genelist.txt"
    response = requests.get(url)
    expected_data = {
        "message": "",
        "data": "#gene\t#drug\nahpC\tINH\neis\tKAN\nembA\tEMB\nembB\tEMB\nembC\tEMB\nfabG1\tINH\ngidB\tSM\ngyrA\tCIP,MOX,OFX\ngyrB\tCIP,MOX,OFX\nkatG\tINH\npncA\tPZA\nrpoB\tRIF\nrpsL\tSM\ntlyA\tCAP\nrpsA\tPZA\nrrs\tSM,KAN,CAP,AK\ninhA\tINH\n",
        "status": "SUCCESS",
    }
    result_data = json.loads(response.text)
    assert_true(expected_data == result_data)


def test_piezo_vcf_01():
    url = "http://localhost:8990/api/v1/resistances/piezo/01?type=piezo"
    response = requests.get(url)
    resulted_data = json.loads(response.text)
    resulted_metadata = resulted_data["data"]["metadata"]
    assert_true(resulted_data["data"]["metadata"]["WGS_PREDICTION_AMI"] == "U")
    assert_true(resulted_data["data"]["metadata"]["WGS_PREDICTION_CAP"] == "U")
    assert_true(resulted_data["data"]["metadata"]["WGS_PREDICTION_CIP"] == "R")
    assert_true(resulted_data["data"]["metadata"]["WGS_PREDICTION_EMB"] == "R")
    assert_true(resulted_data["data"]["metadata"]["WGS_PREDICTION_INH"] == "R")
    assert_true(resulted_data["data"]["metadata"]["WGS_PREDICTION_KAN"] == "U")
    assert_true(resulted_data["data"]["metadata"]["WGS_PREDICTION_LEV"] == "R")
    assert_true(resulted_data["data"]["metadata"]["WGS_PREDICTION_MXF"] == "R")
    assert_true(resulted_data["data"]["metadata"]["WGS_PREDICTION_OFX"] == "R")
    assert_true(resulted_data["data"]["metadata"]["WGS_PREDICTION_PZA"] == "R")
    assert_true(resulted_data["data"]["metadata"]["WGS_PREDICTION_RIF"] == "R")
    assert_true(resulted_data["data"]["metadata"]["WGS_PREDICTION_STM"] == "R")


def test_piezo_vcf_02():
    url = "http://localhost:8990/api/v1/resistances/piezo/02?type=piezo"
    response = requests.get(url)
    resulted_data = json.loads(response.text)
    resulted_metadata = resulted_data["data"]["metadata"]
    assert_true(resulted_data["data"]["metadata"]["WGS_PREDICTION_AMI"] == "U")
    assert_true(resulted_data["data"]["metadata"]["WGS_PREDICTION_CAP"] == "U")
    assert_true(resulted_data["data"]["metadata"]["WGS_PREDICTION_CIP"] == "U")
    assert_true(resulted_data["data"]["metadata"]["WGS_PREDICTION_EMB"] == "S")
    assert_true(resulted_data["data"]["metadata"]["WGS_PREDICTION_INH"] == "R")
    assert_true(resulted_data["data"]["metadata"]["WGS_PREDICTION_KAN"] == "U")
    assert_true(resulted_data["data"]["metadata"]["WGS_PREDICTION_LEV"] == "U")
    assert_true(resulted_data["data"]["metadata"]["WGS_PREDICTION_MXF"] == "U")
    assert_true(resulted_data["data"]["metadata"]["WGS_PREDICTION_OFX"] == "U")
    assert_true(resulted_data["data"]["metadata"]["WGS_PREDICTION_PZA"] == "S")
    assert_true(resulted_data["data"]["metadata"]["WGS_PREDICTION_RIF"] == "S")
    assert_true(resulted_data["data"]["metadata"]["WGS_PREDICTION_STM"] == "R")


def test_piezo_vcf_03():
    url = "http://localhost:8990/api/v1/resistances/piezo/03?type=piezo"
    response = requests.get(url)
    resulted_data = json.loads(response.text)
    assert_true(resulted_data["data"]["metadata"]["WGS_PREDICTION_AMI"] == "S")
    assert_true(resulted_data["data"]["metadata"]["WGS_PREDICTION_CAP"] == "S")
    assert_true(resulted_data["data"]["metadata"]["WGS_PREDICTION_CIP"] == "S")
    assert_true(resulted_data["data"]["metadata"]["WGS_PREDICTION_EMB"] == "S")
    assert_true(resulted_data["data"]["metadata"]["WGS_PREDICTION_INH"] == "S")
    assert_true(resulted_data["data"]["metadata"]["WGS_PREDICTION_KAN"] == "S")
    assert_true(resulted_data["data"]["metadata"]["WGS_PREDICTION_LEV"] == "S")
    assert_true(resulted_data["data"]["metadata"]["WGS_PREDICTION_MXF"] == "S")
    assert_true(resulted_data["data"]["metadata"]["WGS_PREDICTION_OFX"] == "S")
    assert_true(resulted_data["data"]["metadata"]["WGS_PREDICTION_PZA"] == "S")
    assert_true(resulted_data["data"]["metadata"]["WGS_PREDICTION_RIF"] == "R")
    assert_true(resulted_data["data"]["metadata"]["WGS_PREDICTION_STM"] == "S")


def test_piezo_vcf_04():
    url = "http://localhost:8990/api/v1/resistances/piezo/04?type=piezo"
    response = requests.get(url)
    resulted_data = json.loads(response.text)
    resulted_metadata = resulted_data["data"]["metadata"]
    assert_true(resulted_data["data"]["metadata"]["WGS_PREDICTION_AMI"] == "S")
    assert_true(resulted_data["data"]["metadata"]["WGS_PREDICTION_CAP"] == "S")
    assert_true(resulted_data["data"]["metadata"]["WGS_PREDICTION_CIP"] == "S")
    assert_true(resulted_data["data"]["metadata"]["WGS_PREDICTION_EMB"] == "S")
    assert_true(resulted_data["data"]["metadata"]["WGS_PREDICTION_INH"] == "R")
    assert_true(resulted_data["data"]["metadata"]["WGS_PREDICTION_KAN"] == "S")
    assert_true(resulted_data["data"]["metadata"]["WGS_PREDICTION_LEV"] == "S")
    assert_true(resulted_data["data"]["metadata"]["WGS_PREDICTION_MXF"] == "S")
    assert_true(resulted_data["data"]["metadata"]["WGS_PREDICTION_OFX"] == "S")
    assert_true(resulted_data["data"]["metadata"]["WGS_PREDICTION_PZA"] == "S")
    assert_true(resulted_data["data"]["metadata"]["WGS_PREDICTION_RIF"] == "S")
    assert_true(resulted_data["data"]["metadata"]["WGS_PREDICTION_STM"] == "S")


def test_piezo_vcf_05():
    url = "http://localhost:8990/api/v1/resistances/piezo/05?type=piezo"
    response = requests.get(url)
    resulted_data = json.loads(response.text)
    assert_true(resulted_data["data"]["metadata"]["WGS_PREDICTION_AMI"] == "S")
    assert_true(resulted_data["data"]["metadata"]["WGS_PREDICTION_CAP"] == "S")
    assert_true(resulted_data["data"]["metadata"]["WGS_PREDICTION_CIP"] == "S")
    assert_true(resulted_data["data"]["metadata"]["WGS_PREDICTION_EMB"] == "S")
    assert_true(resulted_data["data"]["metadata"]["WGS_PREDICTION_INH"] == "S")
    assert_true(resulted_data["data"]["metadata"]["WGS_PREDICTION_KAN"] == "S")
    assert_true(resulted_data["data"]["metadata"]["WGS_PREDICTION_LEV"] == "S")
    assert_true(resulted_data["data"]["metadata"]["WGS_PREDICTION_MXF"] == "S")
    assert_true(resulted_data["data"]["metadata"]["WGS_PREDICTION_OFX"] == "S")
    assert_true(resulted_data["data"]["metadata"]["WGS_PREDICTION_PZA"] == "R")
    assert_true(resulted_data["data"]["metadata"]["WGS_PREDICTION_RIF"] == "S")
    assert_true(resulted_data["data"]["metadata"]["WGS_PREDICTION_STM"] == "S")


def test_piezo_vcf_06():
    url = "http://localhost:8990/api/v1/resistances/piezo/06?type=piezo"
    response = requests.get(url)
    resulted_data = json.loads(response.text)
    resulted_metadata = resulted_data["data"]["metadata"]
    assert_true(resulted_data["data"]["metadata"]["WGS_PREDICTION_AMI"] == "S")
    assert_true(resulted_data["data"]["metadata"]["WGS_PREDICTION_CAP"] == "S")
    assert_true(resulted_data["data"]["metadata"]["WGS_PREDICTION_CIP"] == "S")
    assert_true(resulted_data["data"]["metadata"]["WGS_PREDICTION_EMB"] == "R")
    assert_true(resulted_data["data"]["metadata"]["WGS_PREDICTION_INH"] == "S")
    assert_true(resulted_data["data"]["metadata"]["WGS_PREDICTION_KAN"] == "S")
    assert_true(resulted_data["data"]["metadata"]["WGS_PREDICTION_LEV"] == "S")
    assert_true(resulted_data["data"]["metadata"]["WGS_PREDICTION_MXF"] == "S")
    assert_true(resulted_data["data"]["metadata"]["WGS_PREDICTION_OFX"] == "S")
    assert_true(resulted_data["data"]["metadata"]["WGS_PREDICTION_PZA"] == "S")
    assert_true(resulted_data["data"]["metadata"]["WGS_PREDICTION_RIF"] == "S")
    assert_true(resulted_data["data"]["metadata"]["WGS_PREDICTION_STM"] == "S")


def test_piezo_vcf_07():
    url = "http://localhost:8990/api/v1/resistances/piezo/07?type=piezo"
    response = requests.get(url)
    resulted_data = json.loads(response.text)
    resulted_metadata = resulted_data["data"]["metadata"]
    assert_true(resulted_data["data"]["metadata"]["WGS_PREDICTION_AMI"] == "S")
    assert_true(resulted_data["data"]["metadata"]["WGS_PREDICTION_CAP"] == "S")
    assert_true(resulted_data["data"]["metadata"]["WGS_PREDICTION_CIP"] == "S")
    assert_true(resulted_data["data"]["metadata"]["WGS_PREDICTION_EMB"] == "S")
    assert_true(resulted_data["data"]["metadata"]["WGS_PREDICTION_INH"] == "S")
    assert_true(resulted_data["data"]["metadata"]["WGS_PREDICTION_KAN"] == "S")
    assert_true(resulted_data["data"]["metadata"]["WGS_PREDICTION_LEV"] == "S")
    assert_true(resulted_data["data"]["metadata"]["WGS_PREDICTION_MXF"] == "S")
    assert_true(resulted_data["data"]["metadata"]["WGS_PREDICTION_OFX"] == "S")
    assert_true(resulted_data["data"]["metadata"]["WGS_PREDICTION_PZA"] == "S")
    assert_true(resulted_data["data"]["metadata"]["WGS_PREDICTION_RIF"] == "U")
    assert_true(resulted_data["data"]["metadata"]["WGS_PREDICTION_STM"] == "S")


def test_piezo_vcf_08():
    url = "http://localhost:8990/api/v1/resistances/piezo/08?type=piezo"
    response = requests.get(url)
    resulted_data = json.loads(response.text)
    resulted_metadata = resulted_data["data"]["metadata"]
    assert_true(resulted_data["data"]["metadata"]["WGS_PREDICTION_AMI"] == "S")
    assert_true(resulted_data["data"]["metadata"]["WGS_PREDICTION_CAP"] == "S")
    assert_true(resulted_data["data"]["metadata"]["WGS_PREDICTION_CIP"] == "S")
    assert_true(resulted_data["data"]["metadata"]["WGS_PREDICTION_EMB"] == "S")
    assert_true(resulted_data["data"]["metadata"]["WGS_PREDICTION_INH"] == "S")
    assert_true(resulted_data["data"]["metadata"]["WGS_PREDICTION_KAN"] == "S")
    assert_true(resulted_data["data"]["metadata"]["WGS_PREDICTION_LEV"] == "S")
    assert_true(resulted_data["data"]["metadata"]["WGS_PREDICTION_MXF"] == "S")
    assert_true(resulted_data["data"]["metadata"]["WGS_PREDICTION_OFX"] == "S")
    assert_true(resulted_data["data"]["metadata"]["WGS_PREDICTION_PZA"] == "S")
    assert_true(resulted_data["data"]["metadata"]["WGS_PREDICTION_RIF"] == "S")
    assert_true(resulted_data["data"]["metadata"]["WGS_PREDICTION_STM"] == "S")


def test_piezo_vcf_09():
    url = "http://localhost:8990/api/v1/resistances/piezo/09?type=piezo"
    response = requests.get(url)
    assert_true(response.ok == False)


def test_piezo_vcf_10():
    url = "http://localhost:8990/api/v1/resistances/piezo/10?type=piezo"
    response = requests.get(url)
    assert_true(response.ok == False)


def test_piezo_vcf_11():
    url = "http://localhost:8990/api/v1/resistances/piezo/11?type=piezo"
    response = requests.get(url)
    assert_true(response.ok == False)


def test_piezo_vcf_12():
    url = "http://localhost:8990/api/v1/resistances/piezo/12?type=piezo"
    response = requests.get(url)
    resulted_data = json.loads(response.text)
    resulted_metadata = resulted_data["data"]["metadata"]
    assert_true(resulted_data["data"]["metadata"]["WGS_PREDICTION_AMI"] == "U")
    assert_true(resulted_data["data"]["metadata"]["WGS_PREDICTION_CAP"] == "U")
    assert_true(resulted_data["data"]["metadata"]["WGS_PREDICTION_CIP"] == "S")
    assert_true(resulted_data["data"]["metadata"]["WGS_PREDICTION_EMB"] == "S")
    assert_true(resulted_data["data"]["metadata"]["WGS_PREDICTION_INH"] == "S")
    assert_true(resulted_data["data"]["metadata"]["WGS_PREDICTION_KAN"] == "U")
    assert_true(resulted_data["data"]["metadata"]["WGS_PREDICTION_LEV"] == "S")
    assert_true(resulted_data["data"]["metadata"]["WGS_PREDICTION_MXF"] == "S")
    assert_true(resulted_data["data"]["metadata"]["WGS_PREDICTION_OFX"] == "S")
    assert_true(resulted_data["data"]["metadata"]["WGS_PREDICTION_PZA"] == "S")
    assert_true(resulted_data["data"]["metadata"]["WGS_PREDICTION_RIF"] == "S")
    assert_true(resulted_data["data"]["metadata"]["WGS_PREDICTION_STM"] == "U")


def test_piezo_vcf_13():
    url = "http://localhost:8990/api/v1/resistances/piezo/13?type=piezo"
    response = requests.get(url)
    resulted_data = json.loads(response.text)
    resulted_metadata = resulted_data["data"]["metadata"]
    assert_true(resulted_data["data"]["metadata"]["WGS_PREDICTION_AMI"] == "S")
    assert_true(resulted_data["data"]["metadata"]["WGS_PREDICTION_CAP"] == "S")
    assert_true(resulted_data["data"]["metadata"]["WGS_PREDICTION_CIP"] == "R")
    assert_true(resulted_data["data"]["metadata"]["WGS_PREDICTION_EMB"] == "S")
    assert_true(resulted_data["data"]["metadata"]["WGS_PREDICTION_INH"] == "S")
    assert_true(resulted_data["data"]["metadata"]["WGS_PREDICTION_KAN"] == "S")
    assert_true(resulted_data["data"]["metadata"]["WGS_PREDICTION_LEV"] == "R")
    assert_true(resulted_data["data"]["metadata"]["WGS_PREDICTION_MXF"] == "R")
    assert_true(resulted_data["data"]["metadata"]["WGS_PREDICTION_OFX"] == "R")
    assert_true(resulted_data["data"]["metadata"]["WGS_PREDICTION_PZA"] == "S")
    assert_true(resulted_data["data"]["metadata"]["WGS_PREDICTION_RIF"] == "S")
    assert_true(resulted_data["data"]["metadata"]["WGS_PREDICTION_STM"] == "S")
