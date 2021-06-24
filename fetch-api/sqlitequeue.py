"""
a queue where the elements are kept in an sqlite database

keeps a record of finished elements

status can be queued, running, success, failure, deleted
"""
import sqlite3
import threading
import time
from datetime import datetime


class SqliteQueue:
    def __init__(self, sqlite3_target):
        self.lock = threading.Lock()
        self.con = sqlite3.connect(sqlite3_target, check_same_thread=False)
        with self.lock, self.con:
            self.con.execute(
                "create table if not exists q (guid primary key not null, status, name, data, progress int, total int, started int, finished, kind)"
            )
            self.con.execute(
                "create view if not exists blah as select guid, status, name, '', progress, total, started, finished, kind from q where status <> 'deleted' order by started asc"
            )
            # set aborted runs to failed state
            self.con.execute("update q set status='failed' where status='running'")
            self.con.commit()

    def push(self, kind, elem, guid, data, pred):
        """
        try to add an element to queue

        if a valid element already exists, return data on that, else add it
        """
        with self.lock, self.con:
            existing = self.con.execute(
                'select * from q where name = ? and kind = ? and status <> "failure" and status <> "deleted"',
                (elem, kind),
            ).fetchall()
            if existing:
                valid = pred(existing)
                if valid:
                    return valid

            self.con.execute(
                "insert into q values (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (guid, "queued", elem, data, 0, 0, time.time(), 0, kind),
            )
            return None

    def get_val(self, guid, col):
        """
        get value of column for guid
        """
        with self.lock, self.con:
            ret = self.con.execute(
                "select {0} from q where guid = ?".format(col), (guid,)
            ).fetchall()
            if ret:
                return ret[0][0]
            else:
                return None

    def set_val(self, guid, col, new_val):
        """
        set value for column for guid
        """
        with self.lock, self.con:
            ret = self.con.execute(
                "update q set {0} = ? where guid = ?".format(col), (new_val, guid)
            )

    def apply_fun(self, guid, col, f):
        """
        apply function to column for guid
        """
        with self.lock, self.con:
            val = self.con.execute(
                "select {0} from q where guid = ?".format(col), (guid,)
            ).fetchall()
            if val:
                val = val[0][0]
                new_val = f(val)
                self.con.execute(
                    "update q set {0} = ? where guid = ?".format(col), (new_val, guid)
                )
                return True
            else:
                return False

    def pop(self, kind):
        """
        remove an element off the queue

        set element status to queued
        """
        while True:
            with self.lock, self.con:
                elems = self.con.execute(
                    'select * from q where status = "queued" and kind = ?', (kind,)
                ).fetchall()
                if elems:
                    guid, name, data = elems[0][0], elems[0][2], elems[0][3]
                    self.con.execute(
                        'update q set status = "running" where guid = ?', (guid,)
                    )
                    return guid, name, data
            time.sleep(5)

    def delete(self, guid):
        with self.lock, self.con:
            self.con.execute('update q set status = "deleted" where guid = ?', (guid,))

    def tolist(self, guid=None):
        """
        get queue list

        for debugging only
        """
        seven_days = 604800.0
        seven_days_ago = datetime.today().timestamp() - seven_days

        ret = dict()
        with self.con:
            if guid:
                elems = self.con.execute(
                    'select * from q where guid = ? and status <> "deleted" order by started asc',
                    (guid,),
                ).fetchall()
            else:
                elems = self.con.execute(
                    "select * from blah where started >= ?", (seven_days_ago,)
                ).fetchall()

            for (
                guid,
                status,
                name,
                data,
                progress,
                total,
                started,
                finished,
                kind,
            ) in elems:
                ret[guid] = {
                    "status": status,
                    "name": name,
                    "data": data,
                    "progress": progress,
                    "total": total,
                    "started": started,
                    "finished": finished,
                    "kind": kind,
                }
        return ret
