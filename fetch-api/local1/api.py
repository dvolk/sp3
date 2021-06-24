"""
/api/fetch/ena/new
/api/fetch/ena/delete
"""

import json
import logging
import pathlib
import uuid

import local1.fetcher
import util
from api import queue
from config import config
from flask import Flask, abort, request


def local1_new(in_accession, request_args):
    glogger = logging.getLogger("fetch_logger")

    fetch_type = request_args.get("fetch_type")
    fetch_rerun = request_args.get("fetch_rerun")
    fetch_range = request_args.get("fetch_range")
    fetch_method = request_args.get("fetch_method")

    if not fetch_type:
        fetch_type = "all"
    if not fetch_rerun:
        fetch_rerun = "false"
    if not fetch_range:
        fetch_range = ""
    if not fetch_method:
        fetch_method = "link"

    data = {
        "fetch_type": fetch_type,
        "fetch_rerun": fetch_rerun,
        "fetch_range": fetch_range,
        "fetch_method": fetch_method,
    }

    glogger.info(data)

    def pred_always_rerun(rows):
        return None

    guid = str(uuid.uuid4())
    ret = queue.push("local1", in_accession, guid, json.dumps(data), pred_always_rerun)

    if ret:
        glogger.info("returning existing run")
        return json.dumps(util.make_api_response("success", data={"existing": ret}))
    else:
        glogger.info("returning new run")
        ret_data = {"guid": guid}
        ret_data.update(data)
        return json.dumps(util.make_api_response("success", data=ret_data))


#
# TODO Should it be async?
# TODO Error checking
# TODO don't process failed fetches
# TODO mark/move deleted fetches
#
def local1_delete(in_guid):
    """
    delete all files in the given guid that aren't in any other fetch guid
    """
    glogger = logging.getLogger("fetch_logger")

    in_guid = str(pathlib.Path(in_guid).name)
    queue.set_val(in_guid, "status", "deleted")

    return json.dumps(util.make_api_response("success", data={}))


def local1_api_start():
    glogger = logging.getLogger("fetch_logger")
    glogger.info("ena_api_start()")
    number_of_threads = 1
    for i in range(0, number_of_threads):
        t = local1.fetcher.local1_Fetcher(i, queue, glogger)
        t.start()
