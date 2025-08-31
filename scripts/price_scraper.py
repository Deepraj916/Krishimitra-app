# scripts/price_scraper.py

import requests
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def get_market_prices():
    """
    This function fetches live agricultural market price data for Maharashtra
    from the official data.gov.in API.
    """
    api_key = os.getenv("DATA_GOV_API_KEY")
    if not api_key:
        print("ERROR: DATA_GOV_API_KEY not found in .env file.")
        return []

    # API endpoint for daily agricultural commodity prices, filtered for Maharashtra
    API_URL = f"https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070?api-key={api_key}&format=json&limit=15&filters[state]=Maharashtra"

    try:
        print("--- Fetching live data from data.gov.in API... ---")
        response = requests.get(API_URL)
        response.raise_for_status()  # Raise an error for bad responses

        data = response.json()
        records = data.get('records', [])

        formatted_data = []
        for record in records:
            # Format the data to match what our webpage expects
            item = {
                'commodity': record.get('commodity', '').strip(),
                'market': record.get('market', '').strip(),
                'price': f"₹{record.get('modal_price', 'N/A')} / Quintal"
            }
            formatted_data.append(item)

        print(f"--- Successfully fetched {len(formatted_data)} records from the API. ---")
        return formatted_data

    except Exception as e:
        print(f"An error occurred while calling the API: {e}")
        return []