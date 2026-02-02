from app.services.meal_agent_smart import generate_smart_meal_plan
from app.services.build_plan_adapter import build_plan_fn
from app.models.meal import MealPlanRequest

class MealController:
    @staticmethod
    def create_meal_plan(request: MealPlanRequest):
        payload = request.dict()
        return generate_smart_meal_plan(payload, build_plan_fn)
