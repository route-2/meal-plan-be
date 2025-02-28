from fastapi import APIRouter
from app.controllers.location_controller import LocationController

router = APIRouter()

@router.post("/store")
def store_user_location(chat_id: str, location_data: dict):
    """ Save user location in Redis """
    return LocationController.store_location(chat_id, location_data)

@router.get("/ingredients")
def get_local_ingredients(chat_id: str):
    """ Get ingredients based on user location """
    return LocationController.get_nearby_ingredients(chat_id)
