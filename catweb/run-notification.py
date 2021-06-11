import os, sys, shlex
import requests
import argh
import logging

def go(username, run_name, status):
    user_data = requests.get(f"http://localhost:13666/get_user?username={username}").json()
    print(user_data)

    if not user_data:
        logging.error(f"run-notification.py: no such user {username}")
        sys.exit(1)
    if "attributes" not in user_data or "email" not in user_data["attributes"]:
        logging.error(f"run-notification.py: misconfigured user {username}")
        sys.exit(1)

    email_to = user_data["attributes"]["email"]
    print(email_to)

    subject = "SP3 run notification"

    body = f"""Dear SP3 user {username}

Your run named "{run_name}" has finished.

If you'd rather not receive run notifications, please email denis.volk@ndm.ox.ac.uk
"""

    cmd = f"/home/ubuntu/env/bin/python /home/ubuntu/sp3/catweb/emails.py send-email-notification {shlex.quote(email_to)} {shlex.quote(subject)} {shlex.quote(body)}"
    os.system(cmd)

if __name__ == "__main__":
    argh.dispatch_command(go)
