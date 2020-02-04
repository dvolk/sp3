'''
A thread that takes elements out of an sqlitequeue
and download accessions from the ENA
'''

import threading
import pandas
import requests
import logging
from io import StringIO
import ftplib
import os
import pathlib
import time
import json

import util
from config import config
import local1.flatten

class local1_Fetcher(threading.Thread):
    def __init__(self, thread_index, queue, glogger):
        threading.Thread.__init__(self)
        self.thread_index = thread_index
        self.queue = queue
        # global logger
        self.glogger = glogger
        # local logger, per-download output to file
        self.tlogger = None

    def run(self):
        '''
        Main thread loop
        '''
        while True:
            guid, accession, data = self.queue.pop('local1')
            tlogger_handlers = self.setup_tlogger(guid)
            self.tlogger.info("started on {0} thread id {1}".format(accession, self.thread_index))
            resp = self.download_files(accession, guid, data)
            self.queue.set_val(guid, "status", resp['status'])
            self.tlogger.info("done with {0}. status: {1}".format(accession, resp['status']))
            self.detach_tlogger_handlers(tlogger_handlers)
        self.glogger.error("thread {0} exited loop".format(self.thread_index))

    def download_files(self, local_path, guid, data):
        '''
        Download files (doesn't do anyting, the files are already there for this fetch type)
        '''

        data = json.loads(data)

        # get a list of all files in the directory
        ok_download_files = list(map(str, list(pathlib.Path(local_path).glob('*'))))
        data['ok_files_len'] = len(ok_download_files)

        self.queue.set_val(guid, "data", json.dumps(data))
        self.queue.set_val(guid, "progress", len(ok_download_files))
        self.queue.set_val(guid, "total", len(ok_download_files))

        flatten_dir = config.get('local_flatten_dir')
        r = local1.flatten.flatten(guid, flatten_dir, guid, self.tlogger, data['fetch_method'])

        return util.make_api_response(status='success', details={})

    def setup_tlogger(self, guid):
        '''
        Setup the thread-local logger. A new logger is created for each
        guid. The log is written to the console and a file.
        '''
        self.tlogger = logging.getLogger("fetch_{0}".format(guid))
        self.tlogger.setLevel(logging.DEBUG)
        c_handlert = logging.StreamHandler()
        f_handlert = logging.FileHandler("logs/{0}.log".format(guid))
        c_handlert.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        f_handlert.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        self.tlogger.addHandler(c_handlert)
        self.tlogger.addHandler(f_handlert)
        return [c_handlert, f_handlert]

    def detach_tlogger_handlers(self, handlers):
        '''
        Detach logging handlers.

        This is the proper way to dispose of a logger?
        '''
        for handler in handlers:
            self.tlogger.removeHandler(handler)
