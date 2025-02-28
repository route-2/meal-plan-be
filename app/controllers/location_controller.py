from fastapi import HTTPException
from app.services.location_agent import get_local_groceries
from app.database import redis_client

class LocationController:
    
    @staticmethod
    def store_location(chat_id: str, location_data: dict):
        """ Store user location in Redis for personalization """
        if not chat_id or not location_data:
            raise HTTPException(status_code=400, detail="Location data is required")
        
        redis_client.set(f"user:{chat_id}:location", str(location_data))
        return {"message": "Location saved successfully"}

    @staticmethod
    def get_nearby_ingredients(chat_id: str):
        """ Fetch location-based ingredients for the user """
        return get_local_groceries(chat_id)
