import csv
import io
from collections import namedtuple
import logging

def parse_nextflow_trace(trace_content):
    traces = list()

    reader = csv.DictReader(io.StringIO(trace_content), delimiter='\t')
    for row in reader:
        traces.append(row)

    return traces
