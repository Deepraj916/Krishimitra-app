#!/usr/bin/env python3
"""
Script to validate Fast2SMS API key format
"""

import os
import re
from dotenv import load_dotenv

def validate_api_key():
    # Load environment variables
    load_dotenv()

    # Get API key
    api_key = os.getenv("FAST2SMS_API_KEY")

    if not api_key:
        print("❌ No API key found in .env file")
        return False

    print(f"API Key: {api_key[:10]}...{api_key[-10:] if len(api_key) > 20 else api_key}")
    print(f"Length: {len(api_key)} characters")

    # Fast2SMS API keys are typically 64-80 characters long and alphanumeric
    if len(api_key) < 20 or len(api_key) > 100:
        print("❌ API key length is unusual. Fast2SMS keys are typically 64-80 characters.")
        return False

    # Check if it contains only valid characters
    if not re.match(r'^[a-zA-Z0-9]+$', api_key):
        print("❌ API key contains invalid characters. Should be alphanumeric only.")
        return False

    print("✅ API key format looks correct")
    print("\nIf you're still getting authentication errors:")
    print("1. Check if your Fast2SMS account is active")
    print("2. Verify you have SMS credits in your account")
    print("3. Make sure you're using the correct API key from your dashboard")
    print("4. Try regenerating the API key in Fast2SMS dashboard")

    return True

if __name__ == "__main__":
    validate_api_key()
