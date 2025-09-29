import os
from dotenv import load_dotenv

load_dotenv()

gmail_address = os.getenv("GMAIL_ADDRESS")
gmail_app_password = os.getenv("GMAIL_APP_PASSWORD")

print("--- Email Environment Check ---")
print(f"GMAIL_ADDRESS: {'Set' if gmail_address else 'NOT SET'}")
if gmail_address:
    print(f"GMAIL_ADDRESS value: {gmail_address[:3]}...{gmail_address[-4:]}")  # Partial for security
print(f"GMAIL_APP_PASSWORD: {'Set' if gmail_app_password else 'NOT SET'}")
if gmail_app_password:
    print("GMAIL_APP_PASSWORD: Set (not printing for security)")
print("--- End Check ---")
