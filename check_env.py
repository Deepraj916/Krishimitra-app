# check_env.py

import os
from dotenv import load_dotenv

print("--- Starting Environment Check ---")

# 1. Print the directory where this script is being run
current_directory = os.getcwd()
print(f"Current Directory: {current_directory}")

# 2. Check if the .env file exists in this directory
env_path = os.path.join(current_directory, '.env')
file_exists = os.path.exists(env_path)
print(f"Does .env file exist here? {file_exists}")

# 3. Try to load the .env file and get the key
if file_exists:
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    print(f"API Key Value: {api_key}")
else:
    print("Could not test for API Key because .env file was not found.")

print("--- End of Check ---")