
from fastapi import HTTPException
from app.services.grocery_agent import generate_grocery_list

class GroceryController:

    @staticmethod
    def create_grocery_list(meal_plan: str):
        """ Generate a structured grocery list based on the meal plan """
        if not meal_plan:
            raise HTTPException(status_code=400, detail="Meal plan is required")
        
        grocery_list = generate_grocery_list(meal_plan)
        return {"grocery_list": grocery_list}
