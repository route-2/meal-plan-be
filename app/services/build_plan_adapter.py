# app/services/build_plan_adapter.py
import json
from typing import Dict, Any, List
from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv(override=True)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def build_plan_fn(*, user_id: str, prefs: Dict[str, Any], candidates: List[Dict[str, Any]], memory: List[str]) -> Dict[str, Any]:
    
    provided = [{"id": r["id"], "title": r.get("title"), "kcal": r.get("kcal"), "time_minutes": r.get("time_minutes"), "tags": r.get("tags", [])}
                for r in candidates]
    allowed_ids = [r["id"] for r in candidates]
    days = int(prefs.get("days") or 7)

    prompt = {
        "task": "Create a meal plan grounded ONLY in allowed_recipe_ids.",
        "days": days,
        "user_memory": memory,
        "provided_recipes": provided,
        "allowed_recipe_ids": allowed_ids,
        "rules": [
            "Use exactly 3 meals per day: breakfast, lunch, dinner.",
            "Every meal MUST use recipe_id from allowed_recipe_ids.",
            "Return valid JSON only."
        ],
        "output_schema": {
            "days": [{"day": 1, "meals": [{"type":"breakfast|lunch|dinner","recipe_id":"string","title":"string"}]}]
        }
    }

    resp = client.chat.completions.create(
        model="gpt-4-turbo",
        temperature=0.2,
        response_format={"type":"json_object"},
        messages=[
            {"role": "system", "content": "You are a grounded meal planner. Use only allowed_recipe_ids."},
            {"role": "user", "content": json.dumps(prompt)},
        ],
    )
    plan = json.loads(resp.choices[0].message.content)

   
    retrieved_set = set(allowed_ids)
    used = set()
    for d in plan.get("days", []):
        for m in d.get("meals", []):
            if m.get("recipe_id"):
                used.add(m["recipe_id"])
    bad = sorted(list(used - retrieved_set))
    if bad:
        
        raise ValueError(f"Planner used invalid recipe_ids: {bad[:5]}")

    return plan
