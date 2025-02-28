from fastapi import APIRouter
from app.controllers.grocery_controller import GroceryController

router = APIRouter()

@router.post("/generate")
def generate_grocery_list(meal_plan: str):
    """ Generate a grocery list based on the meal plan """
    return GroceryController.create_grocery_list(meal_plan)
