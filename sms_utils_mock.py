import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def send_otp_sms_mock(phone_number, otp):
    """
    Mock SMS function for testing purposes.
    This will simulate sending SMS without actually calling the API.
    """
    logger.info(f"MOCK SMS: Would send OTP {otp} to {phone_number}")
    logger.info(f"MOCK SMS: Message: 'Your OTP for password reset is: {otp}. Valid for 5 minutes.'")

    # Simulate successful sending
    print(f"\n{'='*50}")
    print("📱 MOCK SMS SENT 📱")
    print(f"To: {phone_number}")
    print(f"OTP: {otp}")
    print(f"Message: Your OTP for password reset is: {otp}. Valid for 5 minutes.")
    print(f"{'='*50}\n")

    return True

# For testing, you can temporarily replace the import in app.py:
# from sms_utils_mock import send_otp_sms_mock as send_otp_sms
