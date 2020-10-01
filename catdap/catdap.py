import base64
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

    token_last_active_age_max = 3600 # 1h
    token_added_age_max = 24 * 3600  # 24h
    
    if token_last_active_age > token_last_active_age_max or token_added_age > token_added_age_max:
        return False
    if token_last_active_age < 0 or token_added_age < 0:
        return False

    tokens[token]['last_active_epochtime'] = time.time()
    print(tokens)
    return True

# --- passwords ---

def check_password(username, password):
    for user in state['users']:
        if user['name'] == username:
            if bcrypt.verify(password, user['password_hash']):
                return "OK"
            else:
                return "Wrong password"
    else:
        return "User not found"

# --- flask ---

app = Flask(__name__)

@app.route('/')
def root():
    abort(403)

@app.route('/check_user')
def check_user():
    req_fs = ['username', 'password']
    for req_f in req_fs:
        if req_f not in request.args:
            return f"missing arg: {req_f}"

    try:
        username = base64.b64decode(request.args['username']).decode()
        password = base64.b64decode(request.args['password']).decode()
    except Exception as e:
        logging.warning(f"parsing exception: {str(e)}")
        return ""

    username = username[0:255]
    password = password[0:255]

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
    logging.info(f"check_token()! token={token}")
    return json.dumps(is_token_valid(token))

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
