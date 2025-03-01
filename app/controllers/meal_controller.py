from app.services.meal_agent import generate_rag_meal_plan
from app.models.meal import MealPlanRequest

class MealController:
    @staticmethod
    def create_meal_plan(request: MealPlanRequest):
        """Process user request and generate a personalized meal plan."""

       
        user_data = request.dict() 

        
        meal_plan = generate_rag_meal_plan(user_data) 

        return {"meal_plan": meal_plan}
