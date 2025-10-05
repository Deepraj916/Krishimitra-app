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

# --- UPDATED MODELS ---
# Use the current available models: gemini-2.0-flash for both vision and text
vision_model = genai.GenerativeModel('gemini-2.0-flash')
text_model = genai.GenerativeModel('gemini-2.0-flash')
# --------------------

def predict_disease(image_path):
    """
    Takes an image path and returns a detailed JSON object using Gemini AI.
    Includes robust error handling for safety filters and silent failures.
    """
    try:
        img = Image.open(image_path)
        
        prompt = [
            "You are an expert agricultural botanist. Analyze this image of a plant leaf.",
            "Respond ONLY with a single JSON object in the following format:",
            """
            {
              "plant_name": "Name of the plant (e.g., 'Tomato', 'Potato', 'Rose')",
              "disease_name": "Name of the disease or 'Healthy'",
              "remedy_description": "A brief, one or two-sentence suggestion for treatment. If healthy, suggest a general care tip.",
              "product_keyword": "A single, generic search term for a product to treat the disease (e.g., 'fungicide', 'neem oil'). If healthy, this should be null.",
              "fertilizer_name": "Name of the recommended fertilizer to spray (e.g., 'Neem Oil', 'Copper Fungicide'). If healthy or no specific fertilizer needed, use null.",
              "quantity_for_10_liters": "Minimum quantity of the fertilizer to use for 10 liters of water (e.g., '5 ml', '10 grams'). If not applicable, use null."
            }
            """,
            img
        ]
        
        response = vision_model.generate_content(prompt)

        if response.prompt_feedback.block_reason:
            print(f"AI blocked the image. Reason: {response.prompt_feedback.block_reason}")
            return {
                "plant_name": "N/A", "disease_name": "Image Blocked by AI",
                "remedy_description": "The uploaded image was blocked by the AI's safety filters. This can happen with blurry or unusual images. Please try again with a clearer picture.", "product_keyword": None,
                "fertilizer_name": None, "quantity_for_10_liters": None
            }
        
        if not response.text:
            print("AI returned an empty response.")
            return {
                "plant_name": "N/A", "disease_name": "Analysis Failed",
                "remedy_description": "The AI was unable to analyze this image. Please try again with a clearer picture.", "product_keyword": None,
                "fertilizer_name": None, "quantity_for_10_liters": None
            }

        response_text = response.text.strip().replace('```json', '').replace('```', '')
        return json.loads(response_text)
        
    except Exception as e:
        print(f"An error occurred during prediction: {e}")
        return {
            "plant_name": "N/A", "disease_name": "Prediction Error",
            "remedy_description": "A technical error occurred while trying to get a prediction. Please try again.", "product_keyword": None,
            "fertilizer_name": None, "quantity_for_10_liters": None
        }

def get_crop_advice(question):
    """
    Takes a user's question and returns expert agricultural advice from the Gemini AI.
    """
    try:
        prompt = [
            "You are an expert agricultural scientist providing advice to farmers in India.",
            "Your tone should be helpful, clear, and easy to understand.",
            "Provide a practical, actionable answer to the following question.",
            "Format your answer using simple markdown (e.g., use bullet points, bold text). Do not use HTML tags.",
            "---",
            f"Question: {question}"
        ]
        
        response = text_model.generate_content(prompt)
        return response.text
        
    except Exception as e:
        print(f"An error occurred during crop advice generation: {e}")
        return "Sorry, I was unable to process your request at this time. The AI service may be temporarily unavailable."