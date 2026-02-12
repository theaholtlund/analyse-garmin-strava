from email.message import EmailMessage
from config import load_env

def send_email(subject, body):
    msg = EmailMessage()
    msg["From"] = load_env("REPORT_EMAIL_FROM")
    msg["To"] = load_env("REPORT_EMAIL_TO")
    msg["Subject"] = subject
    msg.set_content(body)

    smtp_host = load_env("SMTP_HOST")
    smtp_port = int(load_env("SMTP_PORT", 587))
    smtp_user = load_env("SMTP_USER")
    smtp_pass = load_env("SMTP_PASS")
