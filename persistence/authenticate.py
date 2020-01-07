from ldap3 import Connection

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
