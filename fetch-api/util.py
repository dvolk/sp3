import hashlib
from functools import partial
import subprocess
import urllib
import threading
import pathlib
import shlex
import time

class FTPDownloadThread(threading.Thread):
    def __init__(self, url, out_dir):
        threading.Thread.__init__(self)
        self.download_process = None
        self.url = url
        self.out_dir = out_dir

    def run(self):
        url = urllib.parse.urlparse(self.url)
        assert url.scheme == 'ftp'

        host = url.netloc
        path = pathlib.Path(url.path)
        directory = path.parent
        filename = path.name

        cmd = f"lftp {host} -e 'cd {directory}; set xfer:clobber yes; get {filename} -o {self.out_dir}; exit'"
        self.download_process = subprocess.Popen(shlex.split(cmd), stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        self.stdout, self.stderr = self.download_process.communicate()
        self.returncode = self.download_process.returncode

    def stop(self):
        if not self.download_process:
            return
        self.download_process.kill()

def make_api_response(status, details=None, data=None):
    return { 'status': status, 'details': details, 'data': data }

def file_md5(filename):
    blocksize=2**20
    m = hashlib.md5()
    with open(filename, "rb") as f:
        while True:
            buf = f.read(blocksize)
            if not buf:
                break
            m.update(buf)
    return m.hexdigest()

# "1-5,7" -> [1,2,3,4,5,7]
def range_str_to_list(rstr):
    ret = []
    for elem in rstr.split(','):
        if '-' in elem:
            start, stop = elem.split('-')
            ret += range(int(start), int(stop)+1)
        else:
            ret.append(int(elem))

    return sorted(list(set(ret)))

# [1,2,3,4,5,7] -> "1-5,7"
def lst_to_range_str(lst):
    ret = list()
    start = None
    end = None
    for elem in lst:
        if not start:
            start = elem
            end = elem
        if elem == end or elem == end + 1:
            end = elem
        else:
            if start == end:
                ret.append(str(start))
            else:
                ret.append("{0}-{1}".format(start, end))
            start = elem
            end = elem
    if start:
        if start == end:
            ret.append(str(start))
        else:
            ret.append("{0}-{1}".format(start, end))
    return ",".join(ret)

def list_is_subset(subset, superset):
    return set(subset).issubset(set(superset))

def list_intersection(lst1, lst2):
    return list(set(lst1).intersection(set(lst2)))

def range_str_is_subset(subrstr, superrstr):
    # treat "" as [-inf, inf]
    if superrstr == "":
        return True
    if subrstr == "" and superrstr == "":
        return True
    if subrstr == "" and not superrstr == "":
        return False
    return list_is_subset(range_str_to_list(subrstr), range_str_to_list(superrstr))

def range_str_intersection(rstr1, rstr2):
    return list_intersection(range_str_to_list(rstr1), range_str_to_list(rstr2))
