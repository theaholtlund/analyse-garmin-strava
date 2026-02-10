from email.message import EmailMessage
from config import load_env

def send_email(subject, body):
    msg = EmailMessage()
    msg["From"] = load_env("REPORT_EMAIL_FROM")
    msg["To"] = load_env("REPORT_EMAIL_TO")
    msg["Subject"] = subject
    msg.set_content(body)
