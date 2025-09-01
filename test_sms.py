#!/usr/bin/env python3
"""
Test script for SMS functionality
Run this to debug SMS sending issues
"""

import os
from dotenv import load_dotenv
from sms_utils import send_otp_sms

def test_sms():
    # Load environment variables
    load_dotenv()

    # Check if API key is loaded
    api_key = os.getenv("FAST2SMS_API_KEY")
    print(f"API Key loaded: {'Yes' if api_key else 'No'}")
    print(f"API Key length: {len(api_key) if api_key else 0}")

    if not api_key:
        print("ERROR: FAST2SMS_API_KEY not found in .env file")
        return

    # Test with a sample phone number (replace with your actual number for testing)
    test_phone = input("Enter your mobile number for testing (10 digits): ").strip()

    if not test_phone or len(test_phone) != 10:
        print("Please enter a valid 10-digit mobile number")
        return

    print(f"Testing SMS send to: {test_phone}")

    # Generate test OTP
    import random
    test_otp = str(random.randint(100000, 999999))
    print(f"Test OTP: {test_otp}")

    # Send SMS
    result = send_otp_sms(test_phone, test_otp)

    if result:
        print("✅ SMS sent successfully!")
    else:
        print("❌ SMS sending failed. Check the logs above for details.")

if __name__ == "__main__":
    test_sms()
