import pathlib
import logging
import uuid

import requests

def get_user_pipelines(username, user_pipeline_map):
    for usr in user_pipeline_map:
        if usr['user'] == username:
            if 'pipelines' in usr:
                return usr['pipelines']
    return list()

def get_org_pipelines(org_name, organisations):
    for org in organisations:
        if org['name'] == org_name:
            if 'pipelines' in org:
                return org['pipelines']
    return list()

def path_begins_with(p1, p2):
    if str(p1) >= str(p2):
        if p1[0:len(str(p2))] == p2:
            return True
    return False

def is_public_fetch_source(kind):
    public_fetch_sources = ['ena1']

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

def check_organisation(username, organisations):
    for org in organisations:
        if username in org["users"]:
            return org["name"]
    return None

def get_org_upload_dirs(org_name, organisations):
    logging.warning(str(organisations))
    for org in organisations:
        if org["name"] == org_name:
            return org["upload_dirs"]
    return []

def check_ldap_authentication(form_username, form_password, host):
    '''
    Check user authorization
    '''

    r = requests.get(f"http://127.0.0.1:13666/check_user", params={'username': form_username,
                                                                   'password': form_password })

    try:
        token = str(uuid.UUID(r.text))
        return token
    except:
        return None
