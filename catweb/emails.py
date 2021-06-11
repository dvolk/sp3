import smtplib
import email.utils
from email.message import EmailMessage
import ssl
import logging
import json

import argh

try:
    with open('/home/ubuntu/sp3/catweb/emails.json') as f:
        email_cfg = json.loads(f.read())
except:
    logging.error("emails.json couldn't be opened")
    sys.exit(0)

def send_email_notification(recipient, subject, body):
    SENDER = email_cfg["sender"]
    SENDERNAME = email_cfg["sender_name"]
    RECIPIENT = recipient
    USERNAME_SMTP = email_cfg["smtp_username"]
    password_smtp = email_cfg["smtp_password"]
    HOST = email_cfg["smtp_host"]
    PORT = email_cfg["smtp_port"]
    SUBJECT = subject
    BODY_TEXT = body.replace("\\r", "").replace("\\n", "\r\n")

    # create message container
    msg = EmailMessage()
    msg['Subject'] = SUBJECT
    msg['From'] = email.utils.formataddr((SENDERNAME, SENDER))
    msg['To'] = RECIPIENT
    msg.set_content(BODY_TEXT)

    # Try to send the message.
    try:
        server = smtplib.SMTP(HOST, PORT)
        server.ehlo()
        server.starttls(context=ssl._create_unverified_context())
        server.ehlo()
        server.login(USERNAME_SMTP, password_smtp)
        server.sendmail(SENDER, RECIPIENT, msg.as_string())
        server.close()
    except Exception as e:
        logging.warning(f"Error: {e}")
    else:
        logging.warning(f"Email successfully sent to {recipient}")

def send_email_notification_multiple(recipients_comma_sep, subject, body):
    for recipient in recipients_comma_sep.split(','):
        send_email_notification(recipient, subject, body)

if __name__ == "__main__":
    argh.dispatch_commands([send_email_notification, send_email_notification_multiple])
