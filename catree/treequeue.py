import sqlite3
import time
import threading
import json

con = None
lock = threading.Lock()

def init():
    global con
    con = sqlite3.connect("/db/catree.sqlite", check_same_thread=False)
    with con, lock:
        con.execute("create table if not exists queue(guid, name, provider, status, sample_count int, added int, started int, ended int, user, org)")
        con.execute("create table if not exists run_ids_sample_names(guid, run_ids_sample_names)")
        con.execute("create table if not exists results(guid, result)")
        con.execute("create table if not exists run_sample_tree_index(pipeline_run_uuid, sample_name, tree_guid)")
        con.execute("update queue set status = 'queued' where status = 'running'")

def add(guid, name, provider, run_ids_sample_names, user, org):
    print(type(run_ids_sample_names))
    print(guid, name, provider, run_ids_sample_names, user, org)
    run_ids_sample_names_lst = json.loads(run_ids_sample_names)
    with con, lock:
        con.execute("insert into queue values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (guid, name, provider, "queued", len(json.loads(run_ids_sample_names)), int(time.time()), 0, 0, user, org))
        for run_id_sample_name in run_ids_sample_names_lst:
            pipeline_run_uuid = run_id_sample_name[0:36]
            sample_name = run_id_sample_name[37:]
            con.execute("insert into run_sample_tree_index values (?, ?, ?)", (pipeline_run_uuid, sample_name, guid))
        con.execute("insert into run_ids_sample_names values (?, ?)", (guid, run_ids_sample_names))

def get_trees_containing_sample(run_uuid, sample_name):
    with con, lock:
        return con.execute("select * from queue where guid in (select tree_guid from run_sample_tree_index where pipeline_run_uuid = ? and sample_name = ?) order by added desc", (run_uuid, sample_name)).fetchall()

def get_all():
    with con, lock:
        return con.execute("select * from queue order by added desc").fetchall()

def get(guid):
    with con, lock:
        a = con.execute("select * from queue where guid = ?", (guid,)).fetchone()
        b = con.execute("select run_ids_sample_names from run_ids_sample_names where guid = ?", (guid,)).fetchone()[0]
        c = con.execute("select result from results where guid = ?", (guid,)).fetchone()[0]
    return { "queue_row": a,
             "run_ids_sample_names": b,
             "results": c }

def pop(provider):
    while True:
        with con, lock:
            t = con.execute("select * from queue where status = 'queued' and provider = ? order by added desc", (provider,)).fetchone()
            if t:
                run_ids_sample_names = con.execute("select run_ids_sample_names from run_ids_sample_names where guid = ?", (t[0],)).fetchone()[0]
                con.execute("update queue set status = 'running', started = ? where guid = ?", (int(time.time()), t[0]))
                return t, run_ids_sample_names
        time.sleep(5)

def finish(guid, result):
    with con, lock:
        con.execute("update queue set status = 'done', ended = ? where guid = ?", (int(time.time()), guid))
        con.execute("insert into results values(?, ?)", (guid, json.dumps(result)))
