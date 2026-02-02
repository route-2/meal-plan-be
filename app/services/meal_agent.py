# app/services/meal_agent.py
import os
from typing import Dict, List, Any, Optional

from dotenv import load_dotenv
from openai import OpenAI  

try:
    from app.database import index
except Exception:
    index = None 

load_dotenv(override=True)


client = OpenAI(api_key=os.getenv("OPENAI_API_KEY")) 
print("OPENAI_API_KEY loaded?", bool(os.getenv("OPENAI_API_KEY")))
print("OPENAI_API_KEY starts with:", (os.getenv("OPENAI_API_KEY") or "")[:7])


# -------- Utilities --------

def _as_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, list):
        # coerce items to str and strip
        return [str(x).strip() for x in value if str(x).strip()]
    if isinstance(value, str):
        parts = [x.strip() for x in value.split(",")]
        return [p for p in parts if p]
    return []

def _normalize_payload(body: Dict[str, Any]) -> Dict[str, Any]:
    """
    Accepts both nested shape:
      {"preferences": {"goal","diet","cuisines","budget","exclusions","days", ...}, "chat_id": ...}
    and legacy/flat shape:
      {"diet","cuisinePreference","foodPreference","includeIngredients","budget","ingredientsAtHome", ...}
    Returns a unified dict the prompts will use.
    """
    prefs = body.get("preferences", body)

    # Map multiple possible field names to one canonical set
    goal = prefs.get("goal") or f"{body.get('dietPreference','')}".strip()
    diet = prefs.get("diet") or body.get("diet") or body.get("foodPreference")
    cuisines = prefs.get("cuisines") or body.get("cuisinePreference") or []
    exclusions = prefs.get("exclusions") or body.get("includeIngredients") or []
    budget = prefs.get("budget") or body.get("budget")
    days = prefs.get("days", 7)

    # Ingredients-at-home if you collect it somewhere else
    ingredients_at_home = (
        body.get("available_ingredients")
        or body.get("ingredientsAtHome")
        or prefs.get("ingredientsAtHome")
        or []
    )

    # normalize everything to clean lists/values
    cuisines = _as_list(cuisines)
    exclusions = [e for e in _as_list(exclusions) if e.lower() not in {"no", "none", "nil", "n/a"}]
    ingredients_at_home = _as_list(ingredients_at_home)

    return {
        "chat_id": body.get("chat_id"),
        "goal": goal,                         # e.g., "Losing Weight - Cut"
        "diet": diet,                         # e.g., "Veg"
        "cuisines": cuisines,                 # list[str]
        "budget": float(budget) if budget not in (None, "") else None,
        "exclusions": exclusions,             # list[str]
        "days": int(days) if days else 7,
        "ingredients_at_home": ingredients_at_home,  # list[str]
    }

# -------- Core Generators --------

def generate_meal_plan(user_data: Any) -> str:
    """
    Your original function that uses a *different* shape.
    Kept for reference; not used by the route below.
    If you still use this, pass in a typed object or adapt to dict.
    """
    # If user_data is a dict, adapt here or refactor away
    calories = getattr(user_data, "calories", None) or user_data.get("calories")
    diet = getattr(user_data, "diet", None) or user_data.get("diet")
    sub_goal = getattr(user_data, "sub_goal", None) or user_data.get("sub_goal")
    food_preference = getattr(user_data, "food_preference", None) or user_data.get("food_preference")
    cuisine = getattr(user_data, "cuisine", None) or user_data.get("cuisine")
    exclude_ingredients = getattr(user_data, "exclude_ingredients", None) or user_data.get("exclude_ingredients")
    available_ingredients = (
        getattr(user_data, "available_ingredients", None) or user_data.get("available_ingredients") or []
    )
    home_ingredients = (
        f"Consider these available ingredients: {', '.join(available_ingredients)}."
        if available_ingredients else ""
    )

    prompt = f"""
Create a meal plan with {calories} CALORIES per day for a {diet} diet 
to {sub_goal} weight, strictly adhering to a {food_preference} preference 
and including {cuisine}. Exclude these ingredients strictly: {exclude_ingredients}. 
{home_ingredients}

STRICT FORMAT:
- List exactly 6 options for Breakfast, Lunch, and Dinner.
- Each meal MUST include estimated calories (e.g., "Oatmeal with banana - 350 kcal").
- No extra descriptions, just the meal name and calories.
"""
    resp = client.chat.completions.create(
        model="gpt-4-turbo",
        messages=[
            {"role": "system", "content": "You are a structured meal planning assistant."},
            {"role": "user", "content": prompt},
        ],
    )
    return resp.choices[0].message.content


def generate_rag_meal_plan(body: Dict[str, Any]) -> str:
    """Generate a meal plan using past meals and user preferences (tolerant to payload shapes)."""
    data = _normalize_payload(body)

    
    past_plan = get_past_meals(data.get("chat_id")) if data.get("chat_id") else None
    past_context = f"\nPast plan for personalization:\n{past_plan}\n" if past_plan and "No past meal plans" not in past_plan else ""

    prompt = f"""
Given the following user preferences:
- Goal: {data['goal']}
- Diet: {data['diet']}
- Cuisines: {', '.join(data['cuisines']) or 'any'}
- Allergies/Exclusions: {', '.join(data['exclusions']) or 'none'}
- Budget: {data['budget'] if data['budget'] is not None else 'unspecified'}
- Ingredients at home: {', '.join(data['ingredients_at_home']) or 'none'}
- Planning days: {data['days']}
{past_context}

Output a 7-day plan in PLAIN TEXT (no markdown symbols like #, *, **, _, or backticks).
For each day, list Breakfast, Lunch, and Dinner in this style:

Day 1:
Breakfast: <meal> - <kcal> kcal
Recipe: <2–5 concise steps>

Lunch: <meal> - <kcal> kcal
Recipe: <2–5 concise steps>

Dinner: <meal> - <kcal> kcal
Recipe: <2–5 concise steps>

Keep it readable with blank lines between sections, but DO NOT use markdown formatting.
"""
    resp = client.chat.completions.create(
        model="gpt-4-turbo",
        messages=[
            {"role": "system", "content": "You are a meal planning assistant."},
            {"role": "user", "content": prompt},
        ],
    )
    meal_plan = resp.choices[0].message.content
    return meal_plan



def store_meal_plan(user_id: str, meal_plan: str):
    """Generate an embedding for the meal plan and store it in Pinecone (namespace 'meal-plans')."""
    if not index:
        return {"message": "Pinecone index not configured; skipping store."}

    embedding_response = client.embeddings.create(
        model="text-embedding-3-large",
        input=meal_plan
    )
    embedding = embedding_response.data[0].embedding
    index.upsert(vectors=[(user_id, embedding, {"meal_plan": meal_plan})], namespace="meal-plans")
    return {"message": "Meal plan stored successfully"}


def get_past_meals(user_id: Optional[str] = None) -> str:
    """Retrieve the most similar past meal plan for personalization."""
    if not user_id or not index:
        return "No past meal plans found."

    try:
        # Real similarity search requires a query vector, not an id.
        # If you store per-user last plan, you could also fetch by id. Here we demo similarity.
        probe = f"Past meal plan for user {user_id}"
        emb = client.embeddings.create(model="text-embedding-3-large", input=probe).data[0].embedding

        results = index.query(
            vector=emb,
            top_k=1,
            include_metadata=True,
            namespace="meal-plans",
        )

        matches = results.get("matches") or []
        if matches:
            return matches[0]["metadata"].get("meal_plan", "No past meal plans found.")
        return "No past meal plans found."
    except Exception as e:
        print(f"Pinecone query error: {e}")
        return "No past meal plans found."
