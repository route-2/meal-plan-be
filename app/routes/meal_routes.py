from fastapi import APIRouter
from app.controllers.meal_controller import MealController
from app.models.meal import MealPlanRequest

router = APIRouter()

@router.post("/generate")
def generate_meal_plan(request: MealPlanRequest):
    return MealController.create_meal_plan(request)
