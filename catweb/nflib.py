import csv
from collections import namedtuple
import logging

logger = logging.getLogger("api")

def parse_trace_file(nf_trace_fp):
    traces = list()
    if not nf_trace_fp.is_file():
        logger.warning("trace file {} does not exist".format(nf_trace_fp))
        return []

    with open(str(nf_trace_fp)) as trace_file:
        reader = csv.DictReader(trace_file, delimiter='\t')
        for row in reader:
            traces.append(row)

    return traces

