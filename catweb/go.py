#!/usr/bin/python3

#
# This program is run by nfweb.py. It in turn runs nextflow.
# The purpose of this indirection is to allow the it to detach
# from the web gui so that it can be restarted without existing
# runs being terminated.
#

#
# The web gui uses an sqlite database (table nfruns) to keep
# track of runs
#

import glob
import json
import logging
import os
import pathlib
import queue
import re
import shlex
import shutil
import sqlite3
import subprocess
import sys
import threading
import time
import uuid

import psutil

import config
import db
import nflib

nf_returncode = 1
time_started = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
epochtime_started = time.time()

cfg = config.Config()
cfg.load("config.yaml")


def setup_logging():
    logger = logging.getLogger("go")
    logger.setLevel(logging.DEBUG)
    c_handler = logging.StreamHandler()
    f_handler = logging.FileHandler("api.log")
    c_handler.setFormatter(
        logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    )
    f_handler.setFormatter(
        logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    )
    logger.addHandler(f_handler)
    logger.addHandler(c_handler)
    return logger


logger = setup_logging()
logger.debug("Logging initialized")

# Seconds since 1/1/1970
# https://en.wikipedia.org/wiki/Unix_time
start_epochtime = str(int(time.time()))

# Data to from nfweb.py is passed in here as json
data = json.loads(sys.argv[1])

try:
    with open("/home/ubuntu/sp3/catweb/nfrun_params/" + data["run_uuid"], "w") as f:
        f.write(json.dumps(data, indent=4))
except:
    pass

# Rebind the data
run_uuid = data["run_uuid"]
pipeline_name = data["flow_cfg"]["name"]
run_name = data["run_name"]
flow_cfg = data["flow_cfg"]
user_param_dict = data["user_param_dict"]
user_name = data["user_name"]
context = data["context"]
indir = data["indir"]
readpat = data["readpat"]
contexts = data["contexts"]
print(data["reference_map"])
reference_map = data["reference_map"]

"""
we don't want these configuration in the database
"""
del data["contexts"]
del data["flow_cfg"]

"""
add flow git version to database
"""
data["catweb_git_version"] = cfg.get("catweb_version")
data["flow_git_version"] = flow_cfg["git_version"]
"""
TODO: add container image version
"""

flow_name = flow_cfg["name"]
nf_filename = pathlib.Path(flow_cfg["script"])
output_arg = flow_cfg["output"]["parameter"]
head_node_ip = cfg.get("head_node_ip")

run_context_dict = dict()
for c in flow_cfg["contexts"]:
    run_context_dict[c["name"]] = c
logger.debug(f"run_context_dict: {run_context_dict}")
arguments = run_context_dict[context]["arguments"]

sample_group = "asdf"
prog_dir = pathlib.Path(contexts[context]["prog_dirs"]) / flow_cfg["prog_dir"]
root_dir = pathlib.Path(contexts[context]["root_dirs"])
output_dir = pathlib.Path(contexts[context]["output_dirs"]) / run_uuid


def count_files(indir, readpat):
    # try to find the number of input files based on the existence of
    # parameters indir and readpat
    logger.debug("indir: {0} readpat: {1}".format(indir, readpat))
    if indir:
        if readpat:
            # directory + regex
            if indir[-1] == "/":
                pat = indir + readpat
            else:
                pat = indir + "/" + readpat
        else:
            # directory only
            pat = indir

        # With a pattern like *_alignment.{out,pileup}.vcf,
        # One sample would have two files, one is out.vcf, the other is pileup
        # here we extact just the first one ('out')
        m = re.search("(\{.*),.*\}", pat)
        logger.debug("regex group {0}".format(m))
        if m:
            # replace e.g. *_alignment.{out,pileup}.vcf with *_alignment.out.vcf
            # so we count only one file per nextflow file set (i.e. one sample)
            logger.debug("regex group first elem {0}".format(m.group(1)))
            pat = re.sub(r"(\{.*),*\}", m.group(1), pat)
            pat = re.sub(r"\{", "", pat)
        logger.debug("pat: {0}".format(pat))

        files = glob.glob(pat)
        files_count = len(files)
    else:
        # single file or unknown/incompatible
        # TODO get file name
        pat = ""
        files = ""
        files_count = 1

    return pat, files, files_count


pat, files, files_count = count_files(indir, readpat)

logger.debug(f"File pattern: {pat}")
logger.debug(f"Files counted: {files_count}")

db.insert_files_table(run_uuid, files_count, json.dumps(files))

# Create the run dir
run_dir = root_dir / "runs" / run_uuid
logger.info(f"run_dir: {run_dir}")

os.makedirs(run_dir, exist_ok=True)
os.makedirs(output_dir.parent, exist_ok=True)

# Cache the current directory and then change into the run directory.
oldpwd = pathlib.Path.cwd()
os.chdir(run_dir)


def exit_nicely():
    end_epochtime = str(int(time.time()))
    hist = (time_started, "", "", "ERR", "", "", cmd)
    other = (
        user_name,
        sample_group,
        flow_name,
        context,
        str(root_dir),
        output_arg,
        str(output_dir),
        run_uuid,
        start_epochtime,
        pid,
        ppid,
        end_epochtime,
        run_name,
        json.dumps(data),
    )
    s = hist + other
    db.insert_run(s, run_uuid)
    logger.warning("exit_nicely(): exiting prematurely but nicely")
    exit(-126)


T = None
pid = None
q = queue.Queue()

# This functions runs nextflow, returns the nxtflow pid to the main thread and wait until nextflow finishes
def run_nextflow(queue):
    # user parameters, other than output dir
    user_param_str = str()
    for k, v in user_param_dict.items():
        # ENSURE INPUT DIRECTORY HAS A SLASH AT THE END
        if v == indir:
            if not v[-1] == "/":
                v += "/"
        user_param_str += f"{k} {shlex.quote(v)} "

    if reference_map:
        user_param_str += f" --refmap {shlex.quote(json.dumps(reference_map))} "
    else:
        user_param_str += f" --refmap '' "

    # add pipeline name and run_uuid to nextflow parameters. This allows the nextflow script to add tags
    user_param_str += f" --pipeline_name {shlex.quote(pipeline_name)} "
    user_param_str += f" --run_uuid {shlex.quote(run_uuid)} "
    user_param_str += f" --head_node_ip {shlex.quote(head_node_ip)} "

    logger.debug(f"user_param_str: {user_param_str}")

    nextflow_file = str(prog_dir / nf_filename.name)
    cmd = f"nextflow -q run {shlex.quote(nextflow_file)} -with-trace -with-report -with-timeline -with-dag dag.png {arguments} {user_param_str} {output_arg} {shlex.quote(str(output_dir))}"

    # hyperflow_pipeline = str(prog_dir / nf_filename)
    # cmd = f'{python_exe} {hyperflow_exe} {shlex.quote(hyperflow_pipeline)} -image_dir {image_dir} {user_param_str} {output_arg} {shlex.quote(str(output_dir))}'

    logger.info(f"nextflow cmdline: {cmd}")
    P = subprocess.Popen(shlex.split(cmd))
    ppid = os.getpid()
    logger.info(f"python process pid: {ppid}")
    proc = psutil.Process(ppid)

    # wait until nextflow starts
    while not proc.children():
        logger.debug("waiting for nextflow to start...")
        time.sleep(0.1)

    procchild = proc.children()[0]
    logger.info(f"found child process: {procchild.name()}")

    pid = procchild.pid
    queue.put(cmd)
    queue.put(pid)
    queue.put(ppid)
    logger.info(f"nextflow process pid: {pid}")
    logger.info("thread waiting for nextflow")
    ret = P.wait()
    logger.info(f"nextflow process terminated with code {ret}")
    queue.put(ret)


T = threading.Thread(target=run_nextflow, args=(q,))
T.start()

# continue once nextflow is started and we have the pids
cmd = q.get()
pid = str(q.get())
ppid = str(q.get())

# change into the working directory
os.chdir(root_dir)

stop_nftrace = threading.Event()


def save_nextflow_trace_thread(e):
    while True:
        time.sleep(60)
        if e.is_set():
            break
        try:
            c = open(run_dir / "trace.txt").read()
            db.save_nextflow_trace(run_uuid, c)
            logging.warning(f"go.py: saved trace file for {run_uuid}")
        except Exception as e:
            logging.warning(f"Couldn't save nextflow trace to mongodb: {str(e)}")


T2 = threading.Thread(target=save_nextflow_trace_thread, args=(stop_nftrace,))
T2.start()

# write the nextflow run pid into pids/uuid.pid
with open(run_dir / ".run.pid", "w") as f:
    f.write(pid)

# sqlite nfruns table columns reference
#  1 date_time
#  2 duration
#  3 code_name
#  4 status
#  5 hash
#  6 uuid
#  7 command_line
#  8 user
#  9 sample_group
# 10 workflow
# 11 context
# 12 root_dir
# 13 output_arg
# 14 output_dir
# 15 run_uuid primary key not null
# 16 start_epochtime
# 17 pid
# 18 ppid
# 19 end_epochtime
# 20 output_name
# 21 data_json

end_epochtime = str(int(time.time()))

hist = (time_started, "", "", "-", "", "", cmd)
other = (
    user_name,
    sample_group,
    flow_name,
    context,
    str(root_dir),
    output_arg,
    str(output_dir),
    run_uuid,
    start_epochtime,
    pid,
    ppid,
    end_epochtime,
    run_name,
    json.dumps(data),
)

# add the run to the sqlite database
s = hist + other
db.insert_run(s, run_uuid)

# wait for nextflow to finish
T.join()

end_epochtime = str(int(time.time()))

nf_returncode = str(q.get())

# remove pid file
os.remove(run_dir / ".run.pid")

# update sqlite database with the end results

epochtime_ended = time.time()


def hm_timediff(epochtime_start, epochtime_end):
    t = epochtime_end - epochtime_start
    return f"{int(t//3600)}h {int((t%3600)//60)}m"


hist = (
    time_started,
    hm_timediff(epochtime_started, epochtime_ended),
    "",
    "OK",
    "",
    "",
    cmd,
)
if nf_returncode != "0":
    hist = (time_started, "", "", "ERR", "", "", cmd)
other = (
    user_name,
    sample_group,
    flow_name,
    context,
    str(root_dir),
    output_arg,
    str(output_dir),
    run_uuid,
    start_epochtime,
    pid,
    ppid,
    end_epochtime,
    run_name,
    json.dumps(data),
)
s = hist + other
db.insert_run(s, run_uuid)

logger.info("running nextflow clean -k -f")

os.chdir(run_dir)
os.system("nextflow clean -k -f")

data["output_dir"] = str(output_dir)

for nf_file in ["report.html", "timeline.html"]:
    with open(nf_file, "rb") as f:
        db.save_nextflow_file(run_uuid, f, nf_file)

for report_script in pathlib.Path("/home/ubuntu/sp3/catweb/scripts/").glob("*.py"):
    cmd = f"{str(report_script)} {shlex.quote(json.dumps(data))}"
    logger.warning(f"running report script {cmd}")
    os.system(cmd)

cmd = f"/home/ubuntu/env/bin/python /home/ubuntu/sp3/catweb/run-notification.py {shlex.quote(user_name)} {shlex.quote(run_name)} {shlex.quote('')}"
logging.warning(cmd)
os.system(cmd)

stop_nftrace.set()
T2.join()

# save final trace file one last time
with open(run_dir / "trace.txt") as c:
    db.save_nextflow_trace(run_uuid, c.read())

logger.info("go.py: done")
