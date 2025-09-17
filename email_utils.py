# email_utils.py
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from dotenv import load_dotenv

load_dotenv()

def send_otp_email(recipient_email, otp):
    """Sends an email with the OTP code."""
    sender_email = os.getenv("GMAIL_ADDRESS")
    sender_password = os.getenv("GMAIL_APP_PASSWORD")

    if not sender_email or not sender_password:
        print("CRITICAL ERROR: Gmail credentials not found in environment variables.")
        return False

    message = MIMEMultipart("alternative")
    message["Subject"] = "Your Krishimitra Password Reset OTP"
    message["From"] = f"Krishimitra <{sender_email}>"
    message["To"] = recipient_email

    html = f"""
    <html>
      <body>
        <p>Hi,</p>
        <p>Your One-Time Password (OTP) for resetting your Krishimitra password is:</p>
        <h2 style="color: #2c5e3f; font-size: 24px; letter-spacing: 2px;">{otp}</h2>
        <p>This code is valid for 10 minutes.</p>
        <p>If you did not request this, please ignore this email.</p>
      </body>
    </html>
    """
    
    message.attach(MIMEText(html, "html"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, recipient_email, message.as_string())
        print(f"OTP email sent successfully to {recipient_email}")
        return True
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False

def send_report_to_admin(subject, message_body, user_email="Anonymous"):
    """Sends a user's report to the admin's email."""
    sender_email = os.getenv("GMAIL_ADDRESS")
    sender_password = os.getenv("GMAIL_APP_PASSWORD")
    admin_email = "deeprajabhang@gmail.com" # Your admin email

    if not sender_email or not sender_password:
        print("CRITICAL ERROR: Gmail credentials not found in environment variables.")
        return False

    message = MIMEMultipart()
    message["Subject"] = f"Krishimitra Report: {subject}"
    message["From"] = f"Krishimitra System <{sender_email}>"
    message["To"] = admin_email

    html = f"""
    <html>
      <body>
        <h3>New Report from Krishimitra User</h3>
        <p><strong>From User:</strong> {user_email}</p>
        <p><strong>Subject:</strong> {subject}</p>
        <hr>
        <p><strong>Message:</strong></p>
        <p>{message_body.replace('\\n', '<br>')}</p>
      </body>
    </html>
    """
    message.attach(MIMEText(html, "html"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, admin_email, message.as_string())
        print(f"Report email sent successfully to admin.")
        return True
    except Exception as e:
        print(f"Failed to send report email: {e}")
        return False