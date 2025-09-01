import requests
import os
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def send_otp_sms(phone_number, otp):
    """Sends an OTP to a given phone number using the Fast2SMS API."""
    api_key = os.getenv("FAST2SMS_API_KEY")
    if not api_key:
        logger.error("ERROR: Fast2SMS API Key not found in .env file.")
        return False

    # Clean the phone number - remove any non-numeric characters and ensure it's 10 digits
    clean_number = ''.join(filter(str.isdigit, phone_number))
    if len(clean_number) == 12 and clean_number.startswith('91'):
        clean_number = clean_number[2:]  # Remove country code if present
    elif len(clean_number) != 10:
        logger.error(f"Invalid phone number format: {phone_number} (cleaned: {clean_number})")
        return False

    logger.info(f"Sending OTP {otp} to cleaned number: {clean_number}")

    # Fast2SMS API endpoint and parameters
    url = "https://www.fast2sms.com/dev/bulkV2"

    # Updated parameters based on Fast2SMS API documentation
    payload = {
        "authorization": api_key,
        "message": f"Your OTP for password reset is: {otp}. Valid for 5 minutes.",
        "language": "english",
        "route": "q",  # Quick SMS route
        "numbers": clean_number
    }

    headers = {
        'cache-control': "no-cache"
    }

    try:
        logger.info(f"Making API request to Fast2SMS with payload: {payload}")
        response = requests.post(url, data=payload, headers=headers)
        logger.info(f"Response status code: {response.status_code}")

        if response.status_code == 200:
            response_data = response.json()
            logger.info(f"API Response: {response_data}")

            # Check if the message was sent successfully
            if response_data.get("return") is True:
                logger.info(f"OTP SMS sent successfully to {clean_number}")
                return True
            else:
                logger.error(f"Failed to send SMS: {response_data.get('message', 'Unknown error')}")
                return False
        else:
            logger.error(f"HTTP Error {response.status_code}: {response.text}")
            return False

    except requests.exceptions.RequestException as e:
        logger.error(f"Network error while sending SMS: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error while sending SMS: {e}")
        return False
