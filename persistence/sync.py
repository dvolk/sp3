import yaml
import logging
import uuid
import pathlib
import os

def cmd(s):
    logging.warning(s)
    os.system(s)

def main():
    try:
        instance_conf = pathlib.Path.home() / 'sp3' / 'instance.yaml'
        f = open(instance_conf)
    except Exception as e:
        logging.error(f"Couldn't open instance configuration file {f}")
        logging.error(str(e))
        return 1

    r = f.read()
    conf = yaml.load(r)
    instance_name = conf['name']
    instance_id = conf['id']
    store_host = conf['store']

    local_files_abs = [instance_conf]
    local_files_rel = ['/db/catweb.sqlite',
                       '/db/catreport.sqlite',
                       '/work/reports/catreport/reports',
                       '/work/output']

    # abs files: /a/b/c -> /persistence/{instance_id}/c
    # rel files: /a/b/c -> /persistence/{instance_id}/a/b/c

    for local_file_abs in local_files_abs:
        cmd(f'rsync            -a {local_file_abs} {store_host}:/work/persistence/{instance_id}/')
    for local_file_rel in local_files_rel:
        cmd(f'rsync --relative -a {local_file_rel} {store_host}:/work/persistence/{instance_id}/')

    return 0

if __name__ == '__main__':
    exit(main())
