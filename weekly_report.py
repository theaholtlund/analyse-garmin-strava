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

    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.send_message(msg)


def main():

    status = generate_weekly_running_status()

    body = f"""
    Weekly running status – {status['year']}

    Total distance so far: {status['total_km']} km
    Yearly goal: {status['goal_km']} km

    Expected by now: {status['expected_km_by_now']} km
    Difference: {status['delta_km']} km

    Weeks completed: {status['weeks_passed']}
    """

    send_email(
        subject=f"Running status week {status['weeks_passed']}",
        body=body.strip()
    )
