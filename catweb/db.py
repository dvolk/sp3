import sqlite3
import time
import json
import logging
import copy

logger = logging.getLogger('api')

def setup_db(db_target):
    global con
    con = sqlite3.connect(db_target, check_same_thread=False)
    con.set_trace_callback(logger.debug)
    with con:
        #
        # nextflow runs
        #
        con.execute("CREATE TABLE if not exists nfruns (date_time, duration, code_name, status, hash, uuid, command_line, user, sample_group, workflow, context, root_dir, output_arg, output_dir, run_uuid primary key not null, start_epochtime, pid, ppid, end_epochtime, output_name, data_json);")
        #
        # tracks input and output files for uuid
        #
        con.execute("CREATE TABLE if not exists nffiles (uuid primary key not null, input_files_count int, output_files_count int, input_files, output_files)")
        #
        #
        #
        con.execute("CREATE TABLE if not exists reference_cache (uuid primary key not null, reference_json)")
    return con

def add_to_reference_cache(ref_uuid, reference_json):
    with con:
        con.execute('insert into reference_cache values (?, ?)', (ref_uuid, json.dumps(reference_json)))

def get_reference_cache(ref_uuid):
    ret = con.execute('select reference_json from reference_cache where uuid = ?', (ref_uuid,)).fetchall()
    assert len(ret) == 1
    return ret[0][0]

def get_status(org):
    running = con.execute(f'select * from nfruns where workflow like "{org}-%" and status = "-" order by "start_epochtime" desc').fetchall()
    recent = con.execute(f'select * from nfruns where  workflow like "{org}-%" and status = "OK" order by "start_epochtime" desc limit 5').fetchall()
    failed = con.execute(f'select * from nfruns where  workflow like "{org}-%" and status = "ERR" or status = "FAIL" order by "start_epochtime" desc limit 5').fetchall()
    return (running, recent, failed)

def get_workflow(flow_name):
    return con.execute('select * from nfruns where workflow = ? order by "start_epochtime" desc', (flow_name,)).fetchall()

def delete_run(run_uuid):
    con.execute('delete from nfruns where run_uuid = ?', (run_uuid,))
    con.commit()

def get_run(run_uuid):
    return con.execute('select * from nfruns where run_uuid = ?', (run_uuid,)).fetchall()

def insert_files_table(run_uuid, input_files_count, input_files):
    con.execute('insert into nffiles values (?,?,?,?,?)', (run_uuid, input_files_count, -1, input_files, ""))
    con.commit()

def update_files_table(uuid, output_files_count, output_files):
    con.execute('update nffiles set output_files_count = ? and output_files = ? where uuid = ?', (output_files_count, output_files, uuid))

def get_input_files_count(run_uuid):
    data = con.execute('select input_files_count, output_files_count from nffiles where uuid = ?', (run_uuid,)).fetchall()
    if not data:
        return [-1,-1]
    else:
        return data[0]

def insert_dummy_run(data):
    data2 = copy.deepcopy(data)
    data2.pop('flow_cfg', None)
    # insert a dummy entry into the table so that the user sees that a run is starting
    # this is replaced when the nextflow process starts
    con.execute('insert into nfruns values (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                (time.strftime("%Y-%m-%d %H:%M:%S"),
                 '-',
                 '-',
                 'STARTING',
                 '-',
                 '-',
                 '-',
                 data['user_name'],
                 '',
                 data['flow_cfg']['name'],
                 data['context'],
                 '',
                 '',
                 '',
                 data['run_uuid'],
                 str(int(time.time())),
                 '-',
                 '-',
                 str(int(time.time())),
                 data['run_name'],
                 json.dumps(data2)))
    con.commit()

def insert_meta_run(status_str, data):
    data2 = copy.deepcopy(data)
    data2.pop('flow_cfg', None)
    con.execute('delete from nfruns where run_uuid = ?', (data['run_uuid'],))
    con.execute('insert into nfruns values (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                (time.strftime("%Y-%m-%d %H:%M:%S"),
                 '-',
                 '-',
                 status_str,
                 '-',
                 '-',
                 '-',
                 data['user_name'],
                 '',
                 data['flow_cfg']['name'],
                 data['context'],
                 '',
                 '',
                 '',
                 data['run_uuid'],
                 str(int(time.time())),
                 '-',
                 '-',
                 str(int(time.time())),
                 data['run_name'],
                 json.dumps(data2)))
    con.commit()

def insert_run(s, run_uuid):
    # add the run to the sqlite database
    # delete dummy entry now that nextflow has started
    print ("deleting dummy run")
    con.execute("delete from nfruns where run_uuid = ?", (run_uuid,))
    print ("entering actual run")
    con.execute("insert into nfruns values (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", s)
    con.commit()
