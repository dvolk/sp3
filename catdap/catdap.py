import uuid
import logging
import json
import time

import yaml
from flask import Flask, abort, request
from passlib.hash import bcrypt

# --- state ---

state = dict()

def load_state():
    with open("config.yaml") as f:
        global state
        state = yaml.safe_load(f.read())

def save_state():
    with open("config.yaml", "w") as f:
        global state
        f.write(yaml.dump(state))

# --- transient authentication tokens ---

tokens = dict()

def make_token(username):
    new_token = str(uuid.uuid4())
    tokens[new_token] = { 'added_epochtime': time.time(),
                          'last_active_epochtime': time.time(),
                          'username': username
                         }
    return new_token

def is_token_valid(token):
    if token not in tokens:
        return False

    token_added_age = time.time() - tokens[token]['added_epochtime']
    token_last_active_age = time.time() - tokens[token]['last_active_epochtime']

    token_last_active_age_max = 8 * 3600 # 8h
    token_added_age_max = 5 * 24 * 3600  # 5d

    if token_last_active_age > token_last_active_age_max or token_added_age > token_added_age_max:
        return False
    if token_last_active_age < 0 or token_added_age < 0:
        return False

    tokens[token]['last_active_epochtime'] = time.time()
    print(tokens)
    return True

# --- attributes ---

def get_attributes_from_token(token):
    username = tokens[token]['username']
    attributes = state['users'][username]['attributes']
    return attributes

# --- passwords ---

def check_password(username, password):
    if username not in state['users']:
        return "User not found"
    if bcrypt.verify(password, state['users'][username]['password_hash']):
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
    return json.dumps(list(state['users'].keys()))

@app.route('/get_user')
def get_user():
    username = request.args['username']
    return json.dumps(state['users'][username])

@app.route('/edit_user')
def edit_user():
    username = request.args['username']
    state['users'][username] = json.loads(request.args['user_data'])
    save_state()
    return "OK"

@app.route('/add_user')
def add_user():
    name = request.args['name']
    job_title = request.args['job_title']
    job_address = request.args['job_address']
    referal = request.args['referal']
    country = request.args['country']
    email = request.args['email']
    username = request.args['username']
    password = request.args['password']
    organisation = request.args['organisation']

    if username in state['users']:
        logging.info(f"add_user()! username {username} exists")
        return "Username exists"

    if len(password) < 12:
        logging.info(f"add_user()! password too short (len={len(password)})")
        return "Password is too short (minimum 12 characters)"

    password_hash = bcrypt.hash(password)

    state['users'][username] = {
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
            'email': email } }

    try:
        save_state()
        load_state()
    except:
        del state['users'][username]
        abort(503)

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

@app.route('/check_token/<token>')
def check_token(token):
    if is_token_valid(token):
        attributes = get_attributes_from_token(token)
        logging.info(f"check_token()! token={token},is_valid=true,attributes={attributes}")
        return json.dumps({ "attributes": attributes })
    else:
        logging.info(f"check_token()! token={token},is_valid=false")
        return json.dumps({})

@app.route('/change_password/<token>/<new_password>')
def change_password(token, new_password):
    logging.debug(f"change_password()! token={token}")
    if not is_token_valid(token):
        abort(403)

    if len(new_password) < 12:
        return "Password too short (minimum 12 characters)"

    username = tokens[token]['username']
    logging.debug(f"change_password()! token={token} username={username}")

    if username not in state['users']:
        abort(503)
    user = state['users'][username]

    new_pw_hash = bcrypt.hash(new_password)
    user['password_hash'] = new_pw_hash

    try:
        save_state()
    except:
        abort(503)

    return "OK"

@app.route('/get_organisation')
def get_organisation():
    group = request.args['group']
    org_name = request.args['organisation']
    logging.debug(f"get_organisation()! group={group} organisation={org_name}")
    return state['organisations'][org_name]

# --- main ---

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(message)s')

# don't log requests, as they contain passwords
log = logging.getLogger('werkzeug')
log.disabled = True

def main():
    load_state()
    print(state)
    app.run(port=13666, debug=False)

if __name__ == "__main__":
    main()
