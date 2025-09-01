# email_utils.py
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def send_otp_email(recipient_email, otp):
    """Sends an email with the OTP code."""
    # This now reads the variables loaded by load_dotenv() above
    sender_email = os.getenv("GMAIL_ADDRESS")
    sender_password = os.getenv("GMAIL_APP_PASSWORD")

    if not sender_email or not sender_password:
        # This is the error you are seeing
        print("ERROR: Gmail credentials not found in .env file. Please check your .env file.")
        return False

    # Set up the message
    message = MIMEMultipart("alternative")
    message["Subject"] = "Your Krishimitra Password Reset OTP"
    message["From"] = f"Krishimitra <{sender_email}>"
    message["To"] = recipient_email

    # Create the HTML version of your message
    html = f"""
    <html>
      <body>
        <p>Hi,</p>
        <p>Your One-Time Password (OTP) for resetting your Krishimitra password is:</p>
        <h2 style="color: #2c5e3f; font-size: 24px; letter-spacing: 2px;">{otp}</h2>
        <p>This code will expire in 10 minutes.</p>
      </body>
    </html>
    """
    
    # Add the HTML part to the message
    message.attach(MIMEText(html, "html"))

    try:
        # Create a secure connection with the server and send email
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, recipient_email, message.as_string())
        print(f"OTP email sent successfully to {recipient_email}")
        return True
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False