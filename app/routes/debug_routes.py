from fastapi import APIRouter
from app.services.recipe_corpus import retrieve_recipes_for_request

router = APIRouter()

@router.post("/debug/retrieve-recipes-full")
def debug_retrieve_full(payload: dict):
    user_id = payload.get("user_id") or payload.get("chat_id")
    recipes = retrieve_recipes_for_request(str(user_id), payload, top_k=int(payload.get("top_k", 5)))
    return [
        {
            "id": r["id"],
            "title": r["title"],
            "ingredients_len": len(r.get("ingredients", [])),
            "steps_len": len(r.get("steps", [])),
            "first_ingredient": (r.get("ingredients", [{}])[0].get("name") if r.get("ingredients") else None),
        }
        for r in recipes
    ]
