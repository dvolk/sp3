"""
A thread that takes elements out of an sqlitequeue
and download accessions from the ENA
"""

import ftplib
import json
import logging
import os
import pathlib
import threading
import time
from io import StringIO

import ena1.flatten
import pandas
import requests
import util
from config import config


class ENA_Fetcher(threading.Thread):
    def __init__(self, thread_index, queue, glogger):
        threading.Thread.__init__(self)
        self.thread_index = thread_index
        self.queue = queue
        # global logger
        self.glogger = glogger
        # local logger, per-download output to file
        self.tlogger = None
        self.download_thread = None

    def run(self):
        """
        Main thread loop
        """
        while True:
            guid, accession, data = self.queue.pop("ena1")

            tlogger_handlers = self.setup_tlogger(guid)

            self.tlogger.info(
                "started on {0} thread id {1}".format(accession, self.thread_index)
            )

            resp = self.download_files(accession, guid, data)

            self.queue.set_val(guid, "status", resp["status"])

            self.tlogger.info(
                "done with {0}. status: {1}".format(accession, resp["status"])
            )

            self.detach_tlogger_handlers(tlogger_handlers)

        self.glogger.error("thread {0} exited loop".format(self.thread_index))

    def get_metadata(self, accession, guid):
        """
        Fetch ENA metadata and write it to a file
        """
        ena_url = "http://www.ebi.ac.uk/ena/data/warehouse/filereport?accession={0}&result=read_run".format(
            accession
        )
        self.tlogger.debug(ena_url)
        ena_request = requests.get(ena_url)
        if ena_request.status_code != 200:
            self.tlogger.error(
                "ena returned http code {0} for accession {1}".format(
                    ena_request.status_code, accession
                )
            )
            return util.make_api_response(status="failure")
        rio = StringIO(ena_request.text)
        tbl = pandas.read_csv(rio, sep="\t")
        self.tlogger.info("accession contains {0} entries".format(tbl.shape[0]))

        # write ena metadata table as json to file
        with open("logs/" + guid + ".ena.log", "w") as log:
            log.write(tbl.to_json())

        return util.make_api_response(status="success", data=tbl)

    def get_files(self, tbl, fetch_range):
        """
        Extract paired fastq ftp links from metadata
        """
        ok_files = list()
        bad_files = set()

        self.tlogger.info("scanning metadata table")

        if fetch_range != "":
            tbl = tbl.query("index in {0}".format(util.range_str_to_list(fetch_range)))

        for num, row in tbl.iterrows():
            if "run_accession" not in row:
                self.tlogger.error("row {0} doesn't have run accession".format(num))
                continue

            run_accession = row["run_accession"]

            if "fastq_ftp" not in row or "fastq_md5" not in row:
                self.tlogger.error(
                    "run accession {0} doesn't have fastq_ftp or fastq_md5".format(
                        run_accession
                    )
                )
                bad_files.add(run_accession)
                continue

            try:
                # TODO these rows are sometimes NaN, but why aren't they caught above?
                file_pair = row["fastq_ftp"].split(";")
                md5_pair = row["fastq_md5"].split(";")
            except:
                self.tlogger.error(
                    "run accession {0} doesn't have fastq_ftp or fastq_md5 (2)".format(
                        run_accession
                    )
                )
                bad_files.add(run_accession)
                continue

            if len(file_pair) != 2:
                self.tlogger.warning(
                    "run accession {0} doesn't have paired reads".format(run_accession)
                )
                bad_files.add(run_accession)
                continue
            if len(md5_pair) != 2:
                self.tlogger.warning(
                    "run accession {0} doesn't have paired md5s".format(run_accession)
                )
                bad_files.add(run_accession)
                continue

            file1, file2 = file_pair
            md5_1, md5_2 = md5_pair

            ok_files.append([file1, md5_1])
            ok_files.append([file2, md5_2])

        bad_files = list(bad_files)
        self.tlogger.info(
            "found {0}/{1} ok/bad files in metadata table".format(
                len(ok_files), len(bad_files)
            )
        )

        return util.make_api_response(
            status="success", details={"bad_files": bad_files}, data=ok_files
        )

    def download_file(self, ftp_url, ftp_md5, tbl):
        """
        Download one file from ENA over ftp and check its md5
        """
        ena_download_dir = pathlib.Path(config.get("ena_download_dir"))

        ftp_url = ftp_url.replace("ftp.sra.ebi.ac.uk", "")
        self.tlogger.debug(ftp_url)

        # get file name
        file_dir = "/".join(ftp_url.split("/")[1:-1])
        file_path = "/".join(ftp_url.split("/")[-1:])
        self.tlogger.debug(file_path)
        self.tlogger.debug(file_dir)

        import os

        os.makedirs(str(ena_download_dir / file_dir), exist_ok=True)

        out_filepath = str(ena_download_dir / file_dir / file_path)

        # if file exists:
        #   check md5 sum
        #   if match:
        #     skip download
        #   else
        #     warn log
        if pathlib.Path(out_filepath).exists():
            file_md5 = util.file_md5(out_filepath)
            if file_md5 == ftp_md5:
                self.tlogger.info(
                    "file {0} exists and matches metadata md5".format(out_filepath)
                )
                return util.make_api_response(status="success")
            else:
                self.tlogger.warning(
                    "file {0} exists but does not match metadata md5".format(
                        out_filepath
                    )
                )

        pretend_to_download = False

        if pretend_to_download:
            self.tlogger.info("fake downloading {0}".format(ftp_url))
            time.sleep(1)
            pathlib.Path(out_filepath).touch()
            self.tlogger.debug("ftp md5: N/A")
            self.tlogger.debug("file md5: N/A")
            self.tlogger.info("md5 OK")
            return util.make_api_response(status="success")

        # download
        self.tlogger.info("downloading {0}".format(ftp_url))

        self.download_thread = util.FTPDownloadThread(
            f"ftp://ftp.sra.ebi.ac.uk{ftp_url}", str(pathlib.Path(out_filepath).parent)
        )
        self.download_thread.start()
        self.download_thread.join()
        self.download_thread = None

        # with ftplib.FTP('ftp.sra.ebi.ac.uk') as ftp:
        #    ftp.login()
        #    ftp.retrbinary('RETR {0}'.format(ftp_url), open(out_filepath, 'wb').write)

        # validate md5
        self.tlogger.debug("ftp md5: {0}".format(ftp_md5))
        file_md5 = util.file_md5(out_filepath)
        self.tlogger.debug("file md5: {0}".format(file_md5))
        if file_md5 == ftp_md5:
            self.tlogger.info("md5 OK")
            return util.make_api_response(
                status="success", data={"output_file": out_filepath}
            )
        else:
            self.tlogger.warning("md5 does not match")
            return util.make_api_response(status="failure")

    def download_files(self, accession, guid, data):
        """
        Download files for accession
        """
        data = json.loads(data)

        resp = self.get_metadata(accession, guid)
        if resp["status"] != "success":
            return util.make_api_response(
                status="failure", details={"missing": "metadata"}
            )
        tbl = resp["data"]

        resp = self.get_files(tbl, data["fetch_range"])
        if resp["status"] != "success":
            return resp
        bad_files = resp["details"]["bad_files"]
        ok_files = resp["data"]

        data["bad_files"] = bad_files
        data["ok_files_fastq_ftp"] = [x[0] for x in ok_files]
        data["ok_files_fastq_md5"] = [x[1] for x in ok_files]
        data["ok_files_len"] = len(ok_files)
        data["bad_files_len"] = len(bad_files)

        self.queue.set_val(guid, "data", json.dumps(data))
        self.queue.set_val(guid, "total", len(ok_files))

        ok_download_files = list()
        failed_download_files = list()
        data_ = {}

        if data["fetch_type"] != "metadata":
            for fastq_ftp, fastq_md5 in ok_files:
                #
                # check if data contains 'stop'. If so, discontinue downloading
                #
                d = self.queue.get_val(guid, "data")
                data_ = json.loads(d)
                if "stop" in data_:
                    self.tlogger.info("stopping download")
                    break

                resp = self.download_file(fastq_ftp, fastq_md5, tbl)
                if resp["status"] == "success":
                    ok_download_files.append(fastq_ftp)
                else:
                    failed_download_files.append(fastq_ftp)

                self.queue.apply_fun(guid, "progress", lambda x: x + 1)

        data["failed_download_files"] = failed_download_files
        data["ok_download_files"] = ok_download_files
        self.queue.set_val(guid, "data", json.dumps(data))

        flatten_dir = config.get("ena_flatten_dir")
        r = ena1.flatten.flatten(guid, flatten_dir, guid, self.tlogger)

        status = "success"
        if "stop" in data_:
            status = "failure"

        return util.make_api_response(
            status=status,
            details={
                "bad_files": bad_files,
                "failed_download_files": failed_download_files,
                "ok_download_files": ok_download_files,
            },
        )

    def stop_download(self):
        if self.download_thread:
            self.tlogger.debug("terminating download thread")
            self.download_thread.stop()

    def setup_tlogger(self, guid):
        """
        Setup the thread-local logger. A new logger is created for each
        guid. The log is written to the console and a file.
        """
        self.tlogger = logging.getLogger("fetch_{0}".format(guid))
        self.tlogger.setLevel(logging.DEBUG)
        c_handlert = logging.StreamHandler()
        f_handlert = logging.FileHandler("logs/{0}.log".format(guid))
        c_handlert.setFormatter(
            logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )
        f_handlert.setFormatter(
            logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )
        self.tlogger.addHandler(c_handlert)
        self.tlogger.addHandler(f_handlert)
        return [c_handlert, f_handlert]

    def detach_tlogger_handlers(self, handlers):
        """
        Detach logging handlers.

        This is the proper way to dispose of a logger?
        """
        for handler in handlers:
            self.tlogger.removeHandler(handler)
