import json
import uuid
import sys
import pathlib
import shlex
import os

import requests

import utils
import nflib
import config
import db

cfg = config.Config()
cfg.load('config.yaml')
db.setup_db(cfg.get('db_target'))

def get_user_param_dict_for(user_param_dict, flow_index):
    ret = {}
    for param_key, param_value in user_param_dict.items():
        if not '-and-' in param_key:
            continue
        index, name, arg = param_key.split('-and-')
        if index == flow_index:
            ret[arg] = param_value
    return ret

def run(data):
    db.insert_dummy_run(data)

    log_dir = cfg.get('log_dir')
    utils.mkdir_exist_ok(log_dir)
    log_filename = "{0}.log".format(data['run_uuid'])
    log_file =  str(pathlib.Path(log_dir) / log_filename)
    print(log_file)
    cmd = "( python3 go.py {0} | tee {1} )".format(shlex.quote(json.dumps(data)), log_file)
    os.system(cmd)

def go():
    data = json.loads(sys.argv[1])

    subflows = data['subflows']

    form = data['form']
    base_run_name = data['run_name']
    context = data['context']
    contexts = data['contexts']
    base_user_param_dict = data['user_param_dict']
    user_name = data['user_name']
    base_indir = data['indir']
    base_readpat = data['readpat']
    flow_cfg = data['flow_cfg']
    run_uuid = data['run_uuid']

    '''
    remove subflow configs as we don't want to insert this into the database
    '''
    print(type(subflows))
    data['subflows'] = dict()
    for subflow_name,subflow_cfg in subflows.items():
        data['subflows'][subflow_name] = { 'name': subflow_name,
                                           'git_version': subflow_cfg['git_version'] }

    data['nfweb_version'] = cfg.get('nfweb_version')
    data['subflow_uuids'] = []
    db.insert_meta_run('RUNNING', data)

    for subflow_index, subflow_name in enumerate(flow_cfg['subflows']):
        subflow_cfg = subflows[subflow_name]

        if subflow_index == 0:

            #
            # initial subflow
            #

            run_uuid = str(uuid.uuid4())
            run_name = base_run_name + '_' + str(subflow_index)
            context = context
            user_param_dict = get_user_param_dict_for(form, str(subflow_index))

            sub_data = {
                'run_uuid': run_uuid,
                'run_name': run_name,
                'context': context,
                'contexts': contexts,
                'flow_cfg': subflow_cfg,
                'user_param_dict': user_param_dict,
                'user_name': user_name,
                'indir': base_indir,
                'readpat': base_readpat
                }

            data['subflow_uuids'].append(run_uuid)
            db.insert_meta_run('RUNNING', data)

            run(sub_data)
        else:

            #
            # subsequent subflows
            #

            run_uuid = str(uuid.uuid4())
            run_name = base_run_name + '_' + str(subflow_index)
            context = context
            user_param_dict = get_user_param_dict_for(form, str(subflow_index))
            print(contexts)
            print(last_run_uuid)
            print(subflow_cfg)
            indir = str(pathlib.Path(contexts[context]['output_dirs']) /
                        last_run_uuid /
                        last_fetch_subdir)
            readpat = last_fetch_readpat

            # fucking hell
            for param in subflow_cfg['param']['description']:
                if param['name'] == 'indir':
                    indir_arg = param['arg']
                if param['name'] == 'readpat':
                    readpat_arg = param['arg']

            user_param_dict[indir_arg] = indir
            user_param_dict[readpat_arg] = readpat

            sub_data = {
                'run_uuid': run_uuid,
                'run_name': run_name,
                'context': context,
                'contexts': contexts,
                'flow_cfg': subflow_cfg,
                'user_param_dict': user_param_dict,
                'user_name': user_name,
                'indir': indir,
                'readpat': readpat
                }

            data['subflow_uuids'].append(run_uuid)
            db.insert_meta_run('RUNNING', data)

            run(sub_data)

        last_run_uuid = run_uuid
        if 'output' in subflow_cfg and 'fetch_subdir' in subflow_cfg['output']:
            last_fetch_subdir = subflow_cfg['output']['fetch_subdir']
        if 'output' in subflow_cfg and 'fetch_readpat' in subflow_cfg['output']:
            last_fetch_readpat = subflow_cfg['output']['fetch_readpat']

    db.insert_meta_run('OK', data)

def main():
    go()

if __name__ == '__main__':
    main()
