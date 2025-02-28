from fastapi import APIRouter, Depends
from app.controllers.meal_controller import MealController

router = APIRouter()

@router.post("/generate")
def generate_meal_plan(chat_id: str, user_data: dict):
    """ Generate a meal plan based on user preferences """
    return MealController.create_meal_plan(chat_id, user_data)
