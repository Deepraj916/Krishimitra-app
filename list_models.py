import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("GEMINI_API_KEY not found in .env file.")
genai.configure(api_key=api_key)

try:
    models = genai.list_models()
    for model in models:
        print(model.name)
except Exception as e:
    print(f"Error listing models: {e}")
