from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.grocery_agent import generate_grocery_list

router = APIRouter()

class GroceryRequest(BaseModel):
    meal_plan: str

@router.post("/generate")
async def generate_grocery(request: GroceryRequest):
    """API to generate grocery list from meal plan"""
    if not request.meal_plan:
        raise HTTPException(status_code=400, detail="Meal plan is required")
    grocery_list = generate_grocery_list(request.meal_plan)
    return {"grocery_list": grocery_list}
