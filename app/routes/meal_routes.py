from fastapi import APIRouter
from app.services.meal_agent import store_meal_plan, generate_rag_meal_plan

router = APIRouter()

@router.post("/store-meal")
def store_meal(chat_id: str, meal_plan: str):
    return store_meal_plan(chat_id, meal_plan)

@router.post("/generate-meal")
def generate_meal(chat_id: str, user_data: dict):
    return generate_rag_meal_plan(chat_id, user_data)
