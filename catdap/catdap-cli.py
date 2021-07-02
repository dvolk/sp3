import shlex
import subprocess
import sys

import argh
import pymongo
from passlib.hash import bcrypt


def reset_pw(user):
    myclient = pymongo.MongoClient("mongodb://localhost:27017/")
    mydb = myclient["catdap"]
    accounts_db = mydb["accounts"]

    pw = subprocess.check_output(shlex.split("pwgen -s 16")).decode().strip()
    h = bcrypt.hash(pw)

    accounts_db.update({"username": user}, {"$set": {"password_hash": h}})
    sys.stdout.write(pw)


if __name__ == "__main__":
    argh.dispatch_commands([reset_pw])
