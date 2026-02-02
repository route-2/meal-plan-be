# app/services/meal_agent_smart.py
import time, json
from typing import Dict, Any, List
from collections import defaultdict
from fastapi import HTTPException

from app.services.recipe_corpus import (
    generate_recipe_cards,
    upsert_recipe_cards,
    retrieve_recipes_for_request,
)
from app.services.user_memory import retrieve_memory, store_memory

# ---------- helpers ----------

def _norm_name(name: str) -> str:
    n = (name or "").strip().lower()
    if n in {"tortilla", "tortillas"}:
        return "tortillas"
    return n

def _norm_unit(unit: str) -> str:
    u = (unit or "").strip().lower()
    return {
        "tablespoon": "tbsp",
        "tablespoons": "tbsp",
        "tbsp": "tbsp",
        "teaspoon": "tsp",
        "teaspoons": "tsp",
        "tsp": "tsp",
        "g": "grams",
        "gram": "grams",
        "grams": "grams",
        "clove": "cloves",
        "cloves": "cloves",
        "count": "count",
    }.get(u, u or "unit")

def plan_to_text(plan: Dict[str, Any]) -> str:
    if not plan or "days" not in plan:
        return "No plan generated."
    out = []
    for d in plan["days"]:
        out.append(f"Day {d.get('day')}:")
        for m in d.get("meals", []):
            out.append(f"{str(m.get('type','')).capitalize()}: {m.get('title','')}")
        out.append("")
    return "\n".join(out).strip()

def aggregate_groceries(used_recipe_ids: List[str], recipe_by_id: Dict[str, Any]) -> List[Dict[str, Any]]:
    totals = defaultdict(lambda: defaultdict(float))

    for rid in used_recipe_ids:
        r = recipe_by_id.get(rid) or {}
        for ing in (r.get("ingredients") or []):
            name = _norm_name(str(ing.get("name", "")))
            unit = _norm_unit(str(ing.get("unit") or "unit"))
            if unit in {"to taste", "taste"}:
                continue

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

# ---------- main agent ----------

def generate_smart_meal_plan(payload: Dict[str, Any], build_plan_fn) -> Dict[str, Any]:
    """
    build_plan_fn: a function that takes (user_id, prefs, candidates, memory) and returns
    a structured plan with at least {"days": [...]} and audit used_recipe_ids, or recipe_ids in meals.
    (You can plug in your existing grounded planner here.)
    """

    prefs = payload.get("preferences") or {}
    user_id = payload.get("user_id")
    if not user_id:
        raise HTTPException(status_code=400, detail="Missing user_id")

   
    exclusions = prefs.get("exclusions") or []
    cuisines = prefs.get("cuisines") or []
    diet = prefs.get("diet")
    if diet:
        store_memory(user_id, f"Diet preference: {diet}", mtype="preference")
    if cuisines:
        store_memory(user_id, f"Preferred cuisines: {', '.join(cuisines)}", mtype="preference")
    if exclusions:
        store_memory(user_id, f"Avoid ingredients: {', '.join(exclusions)}", mtype="preference")

    days = int(prefs.get("days") or 7)
    min_needed = max(12, min(30, days * 3))

    # 1) Retrieve current corpus
    candidates = retrieve_recipes_for_request(user_id, prefs, top_k=50)

    # 2) Bootstrap for new users
    if len(candidates) < min_needed:
        recipes = generate_recipe_cards(prefs, n=60)
        ts = int(time.time() * 1000)
        for i, r in enumerate(recipes):
            r["id"] = f"r_{user_id}_{ts}_{i}"
        upsert_recipe_cards(user_id, recipes)

        candidates = retrieve_recipes_for_request(user_id, prefs, top_k=50)

        if len(candidates) < min_needed:
            raise HTTPException(
                status_code=500,
                detail=f"Bootstrap failed: only {len(candidates)} recipes retrieved after generation.",
            )

    # 3) Retrieve memory
    memory = retrieve_memory(
        user_id,
        query="Food preferences, dislikes, time constraints, favorite cuisines, and feedback",
        top_k=6,
    )

    # 4) Build grounded plan using your existing grounded planner logic
    plan = build_plan_fn(user_id=user_id, prefs=prefs, candidates=candidates, memory=memory)

    # 5) Compute groceries deterministically from used recipes
    recipe_by_id = {r["id"]: r for r in candidates}

    # Derive used_ids from plan (either from audit or from day meals)
    used_ids = set()
    for d in plan.get("days", []):
        for m in d.get("meals", []):
            if m.get("recipe_id"):
                used_ids.add(m["recipe_id"])
    used_ids = sorted(list(used_ids))

    grocery_list = aggregate_groceries(used_ids, recipe_by_id)
    kroger_payload = [{"name": g["name"], "quantity": g["qty"], "unit": g["unit"]} for g in grocery_list]

    
    return {
        "meal_plan": plan_to_text(plan),       
        "grocery_list_structured": grocery_list,
        "kroger_payload": kroger_payload,
        "audit": {
            "user_id": user_id,
            "retrieved_count": len(candidates),
            "used_recipe_ids": used_ids,
            "memory_used": memory,
        },
    }
