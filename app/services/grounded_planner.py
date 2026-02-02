# app/services/grounded_planner.py
import os, json
from typing import Dict, Any, List
from collections import defaultdict
from dotenv import load_dotenv
from openai import OpenAI

from app.services.recipe_corpus import retrieve_recipes_for_request
from app.services.user_memory import retrieve_memory

load_dotenv(override=True)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def _norm_name(name: str) -> str:
    n = (name or "").strip().lower()
    # singularize a few common plurals (cheap + effective)
    if n.endswith("tortillas"):
        n = "tortillas"
    elif n.endswith("tortilla"):
        n = "tortillas"
    # optional: normalize other easy ones
    return n

def _norm_unit(unit: str) -> str:
    u = (unit or "").strip().lower()
    mapping = {
        "tbsp": "tbsp",
        "tablespoon": "tbsp",
        "tablespoons": "tbsp",
        "tsp": "tsp",
        "teaspoon": "tsp",
        "teaspoons": "tsp",
        "clove": "cloves",
        "cloves": "cloves",
        "gram": "grams",
        "g": "grams",
        "grams": "grams",
        "ml": "ml",
        "l": "l",
        "count": "count",
    }
    return mapping.get(u, u or "unit")


def _aggregate_grocery_list(used_recipe_ids: List[str], recipe_by_id: Dict[str, Any]) -> List[Dict[str, Any]]:
    totals = defaultdict(lambda: defaultdict(float))  # totals[name][unit] -> qty

    for rid in used_recipe_ids:
        r = recipe_by_id.get(rid) or {}
        for ing in r.get("ingredients", []) or []:
            name = _norm_name(str(ing.get("name", "")))
            unit = _norm_unit(str(ing.get("unit") or "unit"))

            qty = ing.get("qty")

            
            try:
                qty_val = float(qty) if qty not in (None, "") else 1.0
            except Exception:
                qty_val = 1.0

            if name:
                totals[name][unit] += qty_val

    grocery = []
    for name, units in totals.items():
        for unit, qty in units.items():
            grocery.append({"name": name, "qty": round(qty, 2), "unit": unit})

    grocery.sort(key=lambda x: x["name"])
    return grocery

def build_grounded_meal_plan(payload: Dict[str, Any]) -> Dict[str, Any]:
    prefs = payload.get("preferences") or payload

    user_id = (
        payload.get("user_id")
        or payload.get("chat_id")
        or prefs.get("user_id")
        or prefs.get("chat_id")
    )
    if not user_id:
        return {"error": "Missing user_id (or chat_id) in request payload."}

    days = int(prefs.get("days") or payload.get("days") or 3)

    # 1) Retrieve candidate recipes (personalized via filter inside retrieve_recipes_for_request)
    candidates = retrieve_recipes_for_request(str(user_id), prefs, top_k=50)

   

    if len(candidates) < max(5, min(15, days * 3)):
        return {
            "error": "Not enough recipes in corpus. Call /recipes/generate-and-store with a larger count first.",
            "retrieved": len(candidates),
        }

    # 2) Retrieve user memory and inject into planning
    memory = retrieve_memory(
        str(user_id),
        query="Food preferences, dislikes, time constraints, favorite cuisines, and feedback",
        top_k=6,
    )

    # 3) Provide only needed fields to model
    provided = []
    for r in candidates:
        provided.append({
            "id": r["id"],
            "title": r.get("title"),
            "kcal": r.get("kcal"),
            "time_minutes": r.get("time_minutes"),
            "tags": r.get("tags", []),
        })

    allowed_ids = [r["id"] for r in candidates]
    recipe_by_id = {r["id"]: r for r in candidates}

    # 4) LLM compiles ONLY schedule 
    prompt = {
        "task": "Create a meal plan grounded ONLY in provided_recipes.",
        "days": days,
        "user_memory": memory,
        "provided_recipes": provided,
        "allowed_recipe_ids": allowed_ids,
        "rules": [
            "Use exactly 3 meals per day: breakfast, lunch, dinner.",
            "Every meal MUST use recipe_id from allowed_recipe_ids.",
            "Do NOT invent new recipes or recipe_ids.",
            "Try to respect user_memory (avoid dislikes; prefer constraints).",
            "Return valid JSON only."
        ],
        "output_schema": {
            "days": [
                {"day": 1, "meals": [{"type":"breakfast|lunch|dinner","recipe_id":"string","title":"string"}]}
            ],
            "audit": {"used_recipe_ids":["string"]}
        }
    }

    resp = client.chat.completions.create(
        model="gpt-4-turbo",
        temperature=0.2,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": "You are a grounded meal planner. Use only allowed_recipe_ids."},
            {"role": "user", "content": json.dumps(prompt)},
        ],
    )

    plan = json.loads(resp.choices[0].message.content)
    plan.setdefault("audit", {})

    # 5) Hard validation: recipe_ids must be subset of retrieved ids
    used_ids = set()
    for d in plan.get("days", []):
        for m in d.get("meals", []):
            rid = m.get("recipe_id")
            if rid:
                used_ids.add(rid)

    retrieved_set = set(allowed_ids)
    bad = sorted(list(used_ids - retrieved_set))
    if bad:
        return {
            "error": "Planner returned recipe_ids not in retrieved set (invalid grounding).",
            "bad_recipe_ids": bad,
            "retrieved_count": len(allowed_ids),
        }

    plan["audit"]["used_recipe_ids"] = sorted(list(used_ids))
    plan["audit"]["retrieved_recipe_ids"] = allowed_ids
    plan["audit"]["memory_used"] = memory

    # 6) Deterministic groceries + Kroger payload
    grocery_list = _aggregate_grocery_list(plan["audit"]["used_recipe_ids"], recipe_by_id)
    kroger_payload = [{"name": g["name"], "quantity": g["qty"], "unit": g["unit"]} for g in grocery_list]

    plan["grocery_list"] = grocery_list
    plan["kroger_payload"] = kroger_payload

    return plan
