from fastapi import HTTPException
from app.database import redis_client

class UserController:

    @staticmethod
    def save_user_preferences(chat_id: str, preferences: dict):
        """ Save user meal preferences for personalization """
        if not chat_id or not preferences:
            raise HTTPException(status_code=400, detail="Invalid preferences data")
        
        redis_client.set(f"user:{chat_id}:preferences", str(preferences))
        return {"message": "User preferences saved"}

    @staticmethod
    def get_user_preferences(chat_id: str):
        """ Retrieve user preferences from Redis """
        preferences = redis_client.get(f"user:{chat_id}:preferences")
        if not preferences:
            raise HTTPException(status_code=404, detail="No preferences found")
        
        return {"preferences": eval(preferences)}
