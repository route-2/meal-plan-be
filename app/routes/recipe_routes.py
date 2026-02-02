# app/routes/recipe_routes.py
from fastapi import APIRouter
from app.controllers.recipe_controller import RecipeController

router = APIRouter()

router.post("/recipes/generate-and-store")(RecipeController.generate_and_store)
