# catreport

## Description

catreport is a service that takes requests for reports, generates reports,
and serves them.

## Requirements

- python 3.6+
- flask
- requests

## Installation

    virtualenv -p python3 env
    source env/bin/activate
    pip3 install -r requirements.txt

## Running

    python3 main.py

## API

- POST `/req_report/`

Request a report

It is added to the queue and processed one by one

Mandatory inputs: pipeline run uuid, sample name, sample path, report type

- GET `/report/<pipeline_run_uuid>/<sample_name>`

Get 1 report for each report type (if there are multiple reports of the same type, get the latest one)