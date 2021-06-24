"""
Test hypergrid api endpoints and check json result
To run tests:
1. Start hypergrid: python3 hypergrid.py, leave it running on http://127.0.0.1:6000/
2. In another terminal, run nosetests tests
3. Or run nosetests tests/test.py:test_1_status
4. All tests should pass after a fresh start of hypergrid, as it runs in order.
5. To interactively run tests: cd tests; python3; then import test; test.test_1_status()
"""

import json
import time

import requests
from nose.tools import assert_true


def test_1_status():
    url = "http://127.0.0.1:6000/status"
    response = requests.get(url)
    print(response.text)
    expected_result = {"nodes": {}, "queue": []}
    response_result = json.loads(response.text)
    assert_true(expected_result == response_result)
    assert_true(response.ok)


def test_2_addNode():
    url = "http://127.0.0.1:6000/add_node/localhost"
    response = requests.get(url)
    time.sleep(3)
    print(response.text)
    assert_true(response.text == "adding node localhost")
    assert_true(response.ok)


def test_3_submit_long_job():
    url = "http://127.0.0.1:6000/submit"
    response = requests.post(
        url,
        json={
            "name": "test",
            "script": "/home/fan/Code/hypergrid/tests/test_script.sh",
            "mem": "1",
            "work_dir": "/tmp",
        },
    )
    time.sleep(3)
    print(response.text)
    assert_true(response.ok)
    assert_true(int(response.text))


def test_4_terminate_run_job():
    url = "http://127.0.0.1:6000/terminate/1"
    response = requests.get(url)
    time.sleep(3)
    print(response.text)
    expected_output = "terminating"
    response_output = response.text
    assert_true(expected_output == response_output)
    assert_true(response.ok)


def test_5_removeNode():
    url = "http://127.0.0.1:6000/remove_node/localhost"
    response = requests.get(url)
    print(response.text)
    assert_true(response.text == "removed localhost")
    assert_true(response.ok)


def test_6_submit_job_withoutNode():
    url = "http://127.0.0.1:6000/submit"
    response = requests.post(
        url,
        json={
            "name": "test",
            "script": "/home/fan/Code/hypergrid/tests/test_script.sh",
            "mem": "1",
            "work_dir": "/tmp",
        },
    )
    print(response.text)
    assert_true(response.ok)
    assert_true(int(response.text))


def test_7_terminate_queue_job():
    url = "http://127.0.0.1:6000/terminate/2"
    response = requests.get(url)
    print(response.text)
    expected_output = "removed from queue"
    response_output = response.text
    assert_true(expected_output == response_output)
    assert_true(response.ok)
