# ml_model/predictor.py
import google.generativeai as genai
import os
from dotenv import load_dotenv
from PIL import Image
import json

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("GEMINI_API_KEY not found in .env file.")
genai.configure(api_key=api_key)

model = genai.GenerativeModel('gemini-1.5-flash-latest')

def predict_disease(image_path):
    """
    Takes an image path and returns a detailed JSON object with plant, disease, remedy, and keyword.
    """
    try:
        img = Image.open(image_path)
        
        # New, more detailed prompt
        prompt = [
            "You are an expert agricultural botanist. Analyze this image of a plant leaf.",
            "Respond ONLY with a single JSON object in the following format:",
            """
            {
              "plant_name": "Name of the plant (e.g., 'Tomato', 'Potato', 'Rose')",
              "disease_name": "Name of the disease or 'Healthy'",
              "remedy_description": "A brief, one or two-sentence suggestion for treatment. If healthy, suggest a general care tip.",
              "product_keyword": "A single, generic search term for a product to treat the disease (e.g., 'fungicide', 'neem oil', 'bactericide'). If healthy, this should be null."
            }
            """,
            img
        ]
        
        response = model.generate_content(prompt)
        response_text = response.text.strip().replace('```json', '').replace('```', '')
        return json.loads(response_text)
        
    except Exception as e:
        print(f"An error occurred during prediction: {e}")
        return {
            "plant_name": "Unknown",
            "disease_name": "Prediction Error",
            "remedy_description": "Could not get a valid response from the AI model.",
            "product_keyword": None
        }
