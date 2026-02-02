from fastapi import Body, HTTPException
from app.services.recipe_corpus import generate_recipe_cards, upsert_recipe_cards
import time

class RecipeController:
    @staticmethod
    def generate_and_store(payload: dict = Body(...)):
        user_id = payload.get("user_id") or payload.get("chat_id")
        if not user_id:
            raise HTTPException(status_code=400, detail="Missing user_id (or chat_id)")

        recipes = generate_recipe_cards(payload, n=int(payload.get("count", 20)))

        ts = int(time.time() * 1000)
        for i, r in enumerate(recipes):
            r["id"] = f"r_{user_id}_{ts}_{i}"

        stored = upsert_recipe_cards(str(user_id), recipes)
        return {"stored": stored, "sample": recipes[:3]}
