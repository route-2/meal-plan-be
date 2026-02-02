# app/models/meal.py (optional)
from pydantic import BaseModel
from typing import List, Optional

class Preferences(BaseModel):
    user_id: Optional[str] = None
    goal: Optional[str] = None
    diet: Optional[str] = None
    cuisines: List[str] = []
    budget: Optional[float] = None
    exclusions: List[str] = []
    days: int = 7
    ingredientsAtHome: List[str] = []

class MealPlanRequest(BaseModel):
    chat_id: Optional[str] = None
    preferences: Preferences
