import csv
import io
import logging
from collections import namedtuple


def parse_nextflow_trace(trace_content):
    traces = list()

    reader = csv.DictReader(io.StringIO(trace_content), delimiter="\t")
    for row in reader:
        traces.append(row)

    return traces
