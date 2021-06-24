import importlib
import logging
import os
import shlex
import subprocess
import time


def run(cmd):
    logging.warning(cmd)
    return subprocess.check_output(shlex.split(cmd))


def wait_until_server_booted(server_ip):
    while True:
        time.sleep(10)
        try:
            out = run(
                f"ssh -oUserKnownHostsFile=/dev/null -oStrictHostKeyChecking=no {server_ip} uptime"
            )
            print(out)
            time.sleep(30)
            return
        except:
            pass


def run_script(server_ip, script_filename):
    cmd = f"ssh -oUserKnownHostsFile=/dev/null -oStrictHostKeyChecking=no {server_ip} 'bash -s' < {script_filename}"
    logging.warning(cmd)
    return os.system(cmd)


def get_class_from_string(s):
    m = ".".join(s.split(".")[:-1])
    c = s.split(".")[-1:][0]
    try:
        mod = importlib.import_module(m)
        cl = getattr(mod, c)
        return cl
    except Exception as e:
        logging.error(f"couldn't load class: {s}")
        logging.error(str(e))
