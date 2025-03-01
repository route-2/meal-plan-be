from app.services.meal_agent import generate_meal_plan
from app.models.meal import MealPlanRequest

class MealController:
    @staticmethod
    def create_meal_plan(request: MealPlanRequest):
        """Process user request and generate a personalized meal plan."""
        meal_plan = generate_meal_plan(request)
        return {"meal_plan": meal_plan}
