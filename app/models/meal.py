from pydantic import BaseModel, Field
from typing import Optional, List

class MealPlanRequest(BaseModel):
    chat_id: str
    diet: str
    sub_goal: str
    food_preference: str
    cuisine: str
    exclude_ingredients: Optional[str] = Field(None, description="Ingredients to exclude")
    available_ingredients: Optional[List[str]] = Field(None, description="Ingredients at home")
    calories: Optional[int] = Field(None, description="Daily calorie limit")
