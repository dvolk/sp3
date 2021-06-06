import uuid
import logging
import json
import time

import yaml
from flask import Flask, abort, request
from passlib.hash import bcrypt
import waitress
import pymongo

myclient = pymongo.MongoClient("mongodb://localhost:27017/")
mydb = myclient["catdap"]
accounts_db = mydb["accounts"]
organisations_db = mydb["organisations"]
tokens_db = mydb["tokens"]

# --- transient authentication tokens ---

def make_token(username):
    new_token_id = str(uuid.uuid4())
    tokens_db.insert({ 'token_id': new_token_id,
                       'added_epochtime': int(time.time()),
                       'last_active_epochtime': int(time.time()),
                       'username': username })
    return new_token_id

def is_token_valid(token):
    token = tokens_db.find_one({ "token_id": token }, {'_id': False})
    if not token:
        return False

    token_added_age = time.time() - token['added_epochtime']
    token_last_active_age = time.time() - token['last_active_epochtime']

    token_last_active_age_max = 4 * 24 * 3600 # 4d
    token_added_age_max = 30 * 24 * 3600  # 30d

    if token_last_active_age > token_last_active_age_max or token_added_age > token_added_age_max:
        return False
    if token_last_active_age < 0 or token_added_age < 0:
        return False

    tokens_db.update_one({ "token_id": token },
                         { "$set": { "last_active_time": int(time.time()) }})
    return True

# --- attributes ---

def get_attributes_from_token(token):
    token = tokens_db.find_one({ "token_id": token }, {'_id': False})
    if not token:
        return None
    username = token['username']
    account = accounts_db.find_one({ "username": username }, {'_id': False})
    return account["attributes"]

# --- passwords ---

def check_password(username, password):
    account = accounts_db.find_one({ "username": username }, { '_id': False })
    if not account:
        return "User not found"
    if "password_hash" not in account:
        return "No password hash"
    if bcrypt.verify(password, account['password_hash']):
        return "OK"
    else:
        return "Wrong password"

# --- flask ---

app = Flask(__name__)

@app.route('/')
def root():
    abort(403)

@app.route('/get_users')
def get_users():
    accounts = list(accounts_db.find({}, { '_id': False }))
    ret = {}
    for acc in accounts:
        ret[acc["username"]] = acc
    return json.dumps(ret)

@app.route('/get_user')
def get_user():
    username = request.args['username']
    account = accounts_db.find_one({ "username": username }, { '_id': False })
    return json.dumps(account)

@app.route('/edit_user')
def edit_user():
    username = request.args['username']
    user_data = json.loads(request.args['user_data'])
    accounts_db.update_one({ "username": username },
                           { "$set": user_data })
    return "OK"

@app.route('/add_user')
def add_user():
    name = request.args.get('name')
    job_title = request.args.get('job_title')
    job_address = request.args.get('job_address')
    referal = request.args.get('referal')
    country = request.args.get('country')
    email = request.args.get('email')
    username = request.args.get('username')
    password = request.args.get('password')
    organisation = request.args.get('organisation')

    if not (name and email and organisation and username and password):
        return "err-missing_data"

    if accounts_db.find_one({ "username": username }, { '_id': False }):
        return "err-username_exists"

    if len(username) < 3:
        return "err-username_too_short"
    if len(username) > 64:
        return "err-username_too_long"

    if len(password) < 12:
        return "err-password_too_short"

    password_hash = bcrypt.hash(password)

    accounts_db.insert_one(
        { "username": username,
          'password_hash': password_hash,
          'attributes': {
              'catweb_user': True,
              'catweb_organisation': organisation,
              'date_added': str(int(time.time())),
              'date_expires': None,
              'requires_review': True,
              'name': name,
              'job_title': job_title,
              'job_address': job_address,
              'referal': referal,
              'country': country,
              'email': email } })
    return "OK"

@app.route('/check_user')
def check_user():
    req_fs = ['username', 'password']
    for req_f in req_fs:
        if req_f not in request.args:
            return f"missing arg: {req_f}"

    username = request.args['username'][0:255]
    password = request.args['password'][0:255]

    logging.info(f"check_user()! username={username}")

    is_valid = check_password(username, password)

    t = None
    if is_valid == "OK":
        t = make_token(username)

    logging.info(f"check_user()! username={username},is_valid={is_valid},token={t}")

    if is_valid == "OK":
        return t
    return ""

@app.route('/check_token/<token_id>')
def check_token(token_id):
    if is_token_valid(token_id):
        attributes = get_attributes_from_token(token_id)
        logging.info(f"check_token()! token={token_id},is_valid=true")
        return json.dumps({ "attributes": attributes })
    else:
        logging.info(f"check_token()! token={token_id},is_valid=false")
        return json.dumps({})

@app.route('/change_password/<token_id>')
def change_password(token_id):
    logging.debug(f"change_password()! token={token_id}")
    if not is_token_valid(token_id):
        abort(403)

    if 'new_password' not in request.args:
        abort(404)

    new_password = request.args['new_password']

    if len(new_password) < 12:
        return "Password too short (minimum 12 characters)"

    token = tokens_db.find_one({ "token_id": token_id }, {'_id': False})
    username = token['username']
    logging.debug(f"change_password()! token={token_id} username={username}")

    account = accounts_db.find_one({ "username": username }, { '_id': False })
    if not account:
        return "Account not found"

    new_pw_hash = bcrypt.hash(new_password)
    accounts_db.update_one({ "username": username },
                           { "$set": {
                               "password_hash": new_pw_hash } })

    return "OK"

@app.route('/get_organisation')
def get_organisation():
    group = request.args['group']
    org_name = request.args['organisation']

    logging.debug(f"get_organisation()! group={group} organisation={org_name}")

    organisation = organisations_db.find_one({ "name": org_name }, { '_id': False })
    logging.warning(organisation)
    if not organisation:
        return json.dumps({})

    return json.dumps(organisation)

# --- main ---

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(message)s')

def main():
    waitress.serve(app, listen='127.0.0.1:13666')

if __name__ == "__main__":
    main()
