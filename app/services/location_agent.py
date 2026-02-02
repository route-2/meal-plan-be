import requests
from app.database import redis_client  
import json


def get_local_groceries(chat_id):
    location_data = redis_client.get(f"user:{chat_id}:location")
    if not location_data:
        return "No location found."

    location = eval(location_data)  # Convert string back to dict
    
    city = location["address"]["city"]
    
    response = requests.get(f"https://api.kroger.com/v1/products?filter.location={city}")
    return response.json()
