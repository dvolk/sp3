import pathlib
import logging
import uuid

import requests

def get_org_pipelines(org_name, organisations):
    return organisations[org]['pipelines']

def path_begins_with(p1, p2):
    if str(p1) >= str(p2):
        if p1[0:len(str(p2))] == p2:
            return True
    return False

def is_public_fetch_source(kind):
    public_fetch_sources = ['ena1', 'ena2']

    return kind in public_fetch_sources

def user_can_see_upload_dir(user_dict, p2):
    if path_begins_with(p2, '/data/inputs/users/{user_dict["name"]}'):
        if pathlib.Path(p2).exists():
            return True
    for p1 in user_dict["upload_dirs"]:
        #logging.warning(f"{user_dict} {p1} {p2}")
        if path_begins_with(p2, p1):
            return True
    return False

def get_org_upload_dirs(org_name, organisations):
    return organisations[org_name]["upload_dirs"]

def get_organisation(org_name):
    org_data = requests.get(f"http://127.0.0.1:13666/get_organisation",
                            params={'group': 'catweb',
                                    'organisation': org_name}).json()
    if not org_data:
        return None
    return org_data['attributes']

def attributes_from_user_token(token):
    r = requests.get(f"http://127.0.0.1:13666/check_token/{token}").json()
    if 'attributes' not in r:
        return None
    return r['attributes']

def check_authentication(form_username, form_password):
    r = requests.get(f"http://127.0.0.1:13666/check_user",
                     params={'username': form_username,
                             'password': form_password })

    try:
        token = str(uuid.UUID(r.text))
        return token
    except:
        return None
