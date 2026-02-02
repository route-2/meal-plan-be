# app/routes/grounded_meal_routes.py
from fastapi import APIRouter
from app.services.grounded_planner import build_grounded_meal_plan

router = APIRouter()

@router.post("/grounded")
def grounded(payload: dict):
    return build_grounded_meal_plan(payload)
