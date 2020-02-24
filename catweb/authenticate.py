from ldap3 import Connection
import logging

def path_begins_with(p1, p2):
    if str(p1) >= str(p2):
        if p1[0:len(str(p2))] == p2:
            return True
    return False

def is_public_fetch_source(kind):
    public_fetch_sources = ['ena1']

    return kind in public_fetch_sources

def user_can_see_upload_dir(user_dict, p2):
    for p1 in user_dict["upload_dirs"]:
        logging.warning(f"{user_dict} {p1} {p2}")
        if path_begins_with(p2, p1):
            return True

def check_organisation(username, org_map):
    for org in org_map:
        if username in org["users"]:
            return org["name"]
    return None

def get_org_upload_dirs(org_name, org_map):
    logging.warning(str(org_map))
    for org in org_map:
        if org["name"] == org_name:
            return org["upload_dirs"]
    return []

def check_ldap_authentication(form_username, form_password, host):
    '''
    Check user authorization
    '''
    conn = Connection(host,
                      user=form_username,
                      password=form_password,
                      read_only=True)
    if conn.bind():
        return True
    else:
        return False
