from fastapi import APIRouter
from app.controllers.user_controller import UserController

router = APIRouter()

@router.post("/preferences")
def save_preferences(chat_id: str, preferences: dict):
    """ Save user meal preferences """
    return UserController.save_user_preferences(chat_id, preferences)

@router.get("/preferences")
def get_preferences(chat_id: str):
    """ Retrieve user meal preferences """
    return UserController.get_user_preferences(chat_id)
