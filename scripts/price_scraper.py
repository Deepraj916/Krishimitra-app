# scripts/price_scraper.py
import requests
import os
from dotenv import load_dotenv

load_dotenv()

def get_market_prices(market=None, commodity=None, date_str=None):
    """
    Fetches live agricultural market price data from the data.gov.in API,
    with optional filters for market, commodity, AND date.
    """
    api_key = os.getenv("DATA_GOV_API_KEY")
    if not api_key:
        print("ERROR: DATA_GOV_API_KEY not found in .env file.")
        return []

    base_url = f"https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070?api-key={api_key}&format=json"
    
    # Dynamically add filters to the URL
    filters = "&filters[state]=Maharashtra"
    if market:
        filters += f"&filters[market]={market}"
    if commodity:
        filters += f"&filters[commodity]={commodity}"
    
    # --- THIS IS THE NEW PART ---
    # Add a date filter if one is provided
    if date_str:
        filters += f"&filters[arrival_date]={date_str}"
    # --------------------------
    
    limit = "&limit=50"
    API_URL = base_url + filters + limit

    try:
        print(f"--- Fetching data from API with URL: {API_URL} ---")
        response = requests.get(API_URL)
        response.raise_for_status()
        data = response.json()
        records = data.get('records', [])
        
        formatted_data = []
        for record in records:
            item = {
                'commodity': record.get('commodity', '').strip(),
                'market': record.get('market', '').strip(),
                'price': f"₹{record.get('modal_price', 'N/A')} / Quintal"
            }
            formatted_data.append(item)
        
        print(f"--- Successfully fetched {len(formatted_data)} records. ---")
        return formatted_data

    except Exception as e:
        print(f"An error occurred while calling the API: {e}")
        return []