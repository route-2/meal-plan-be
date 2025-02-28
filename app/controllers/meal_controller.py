from fastapi import HTTPException
from app.services.meal_agent import generate_rag_meal_plan, store_meal_plan

class MealController:
    
    @staticmethod
    def create_meal_plan(user_id: str, user_data: dict):
        """ Generate a personalized meal plan and store it in Pinecone """
        if not user_id or not user_data:
            raise HTTPException(status_code=400, detail="Invalid input data")
        
        meal_plan = generate_rag_meal_plan(user_id, user_data)
        store_meal_plan(user_id, meal_plan)
        return {"meal_plan": meal_plan}