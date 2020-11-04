'''
/api/fetch/ena/new
/api/fetch/ena/delete
'''

import logging
import uuid
import json
import pathlib

from flask import Flask, abort, request
from api import queue
import util
from config import config
import ena2.fetcher
import datetime

def ena2_new(guid, request_args):
    glogger = logging.getLogger("fetch_logger")
    glogger.debug(f'request_args: {request_args}')

    fetch_name = request_args['fetch_name']
    glogger.debug(f'fetch_name: {fetch_name}')

    fetch_samples = request_args['fetch_samples']
    glogger.debug(f'fetch_samples: {fetch_samples}')

    def pred_always_rerun(rows):
        return None
    ret = queue.push('ena2', fetch_name , guid, json.dumps(request_args), pred_always_rerun)

    if ret:
        glogger.info("returning existing run")
        return json.dumps(util.make_api_response('success', data={ 'existing': ret }))
    else:
        glogger.info("returning new run")
        ret_data = { 'guid': guid }
        return json.dumps(util.make_api_response('success', data=ret_data))

# TODO Should it be async?
# TODO Error checking
# TODO don't process failed fetches
# TODO mark/move deleted fetches
#
def ena2_delete(in_guid):
    '''
    delete all files in the given guid that aren't in any other fetch guid
    '''
    glogger = logging.getLogger("fetch_logger")

    in_guid = str(pathlib.Path(in_guid).name)

    # get all files for guid
    # for all rows in table
    #    get all files
    # delete set difference (all files for guid) (all files in all guids)

    all_guids = list()
    for row in queue.tolist():
        all_guids.append(row)

    all_files = set()
    in_guid_files = set()

    for guid in all_guids:
        print(in_guid, guid, in_guid == guid)
        r = queue.tolist(guid)[guid]
        if r['status'] in ['failure', 'deleted']:
            continue
        r = r['data']
        data = json.loads(r)
        if 'ok_download_files' not in data:
            continue
        files = set(data['ok_download_files'])
        if guid == in_guid:
            in_guid_files = files
        else:
            all_files = all_files.union(files)

    files_to_delete = in_guid_files.difference(all_files)

    glogger.debug("guid files: {0}".format(in_guid_files))
    glogger.debug("all files: {0}".format(all_files))
    glogger.debug("files to delete: {0}".format(files_to_delete))

    deleted = dict()
    not_found = dict()
    for f in files_to_delete:
        s = f.replace('ftp.sra.ebi.ac.uk/', '')
        s = pathlib.Path(config.get('ena_download_dir')) / s
        try:
            s.unlink()
            deleted[f] = str(s)
        except FileNotFoundError:
            glogger.warning("delete fetch guid {0} file {1} doesn't exist".format(in_guid, s))
            not_found[f] = str(s)

    queue.set_val(in_guid, 'status', 'deleted')

    return json.dumps(util.make_api_response('success', data={ 'deleted': deleted, 'not_found': not_found }))

t = None

def ena2_api_start():
    glogger = logging.getLogger("fetch_logger")
    glogger.info("ena_api_start()")
    number_of_threads = 1
    for i in range(0, number_of_threads):
        t = ena2.fetcher.ENA_Fetcher(i, queue, glogger)
        t.start()

def stop_download():
    if t:
        t.stop_download()
