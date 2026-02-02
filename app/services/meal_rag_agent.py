# app/services/meal_rag_agent.py
from typing import Dict, Any
from app.services.recipe_rag import (
    build_recipe_query, retrieve_recipes, retrieve_user_memory,
    select_recipes, compile_grounded_plan
)

def generate_grounded_meal_plan(body: Dict[str, Any]) -> Dict[str, Any]:
    """
    Orchestrates RAG:
      - retrieves recipes
      - retrieves user memory
      - selects recipes
      - compiles plan JSON
    """
   
    data = body.get("preferences", body)

    days = int(data.get("days") or 7)
    chat_id = body.get("chat_id") or data.get("chat_id")

    query = build_recipe_query({
        "goal": data.get("goal"),
        "diet": data.get("diet"),
        "cuisines": data.get("cuisines", []),
        "exclusions": data.get("exclusions", []),
        "budget": data.get("budget"),
        "ingredients_at_home": data.get("ingredients_at_home", body.get("available_ingredients", [])),
        "days": days,
    })

    candidates = retrieve_recipes(query, k=35)
    memory = retrieve_user_memory(str(chat_id), k=6) if chat_id else []

    selected = select_recipes(candidates, target_meals=days * 3, data={
        "ingredients_at_home": data.get("ingredients_at_home", []),
        "exclusions": data.get("exclusions", []),
    })

    plan = compile_grounded_plan({
        "goal": data.get("goal"),
        "diet": data.get("diet"),
        "cuisines": data.get("cuisines", []),
        "exclusions": data.get("exclusions", []),
        "budget": data.get("budget"),
        "ingredients_at_home": data.get("ingredients_at_home", []),
        "days": days,
    }, selected, memory)

    return plan
