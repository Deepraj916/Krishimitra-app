# email_utils.py
import os
from dotenv import load_dotenv
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

load_dotenv()

def send_otp_email(recipient_email, otp):
    """Sends an OTP email using the SendGrid API."""
    # Your From Email must be the one you verified as a "Sender Identity" on SendGrid
    from_email = os.getenv('GMAIL_ADDRESS') 
    message = Mail(
        from_email=from_email,
        to_emails=recipient_email,
        subject='Your Krishimitra Password Reset OTP',
        html_content=f"""
            <h3>Hi,</h3>
            <p>Your One-Time Password (OTP) for resetting your Krishimitra password is:</p>
            <h2 style='color: #2c5e3f; font-size: 24px; letter-spacing: 2px;'>{otp}</h2>
            <p>This code is valid for 10 minutes.</p>
        """
    )
    try:
        sg = SendGridAPIClient(os.getenv('SENDGRID_API_KEY'))
        response = sg.send(message)
        print(f"OTP email sent to {recipient_email}, Status Code: {response.status_code}")
        return True
    except Exception as e:
        print(f"Failed to send email via SendGrid: {e}")
        return False

def send_report_to_admin(subject, message_body, user_email="Anonymous"):
    """Sends a report email to the admin using the SendGrid API."""
    admin_email = "deeprajabhang@gmail.com"
    from_email = os.getenv('GMAIL_ADDRESS') # Must be your verified SendGrid sender
    message = Mail(
        from_email=from_email,
        to_emails=admin_email,
        subject=f'Krishimitra Report: {subject}',
        html_content=f"""
            <h3>New Report from Krishimitra User</h3>
            <p><strong>From User:</strong> {user_email}</p>
            <p><strong>Subject:</strong> {subject}</p>
            <hr>
            <p><strong>Message:</strong></p>
            <p>{message_body.replace('\\n', '<br>')}</p>
        """
    )
    try:
        sg = SendGridAPIClient(os.getenv('SENDGRID_API_KEY'))
        response = sg.send(message)
        print(f"Report email sent to admin, Status Code: {response.status_code}")
        return True
    except Exception as e:
        print(f"Failed to send report email via SendGrid: {e}")
        return False