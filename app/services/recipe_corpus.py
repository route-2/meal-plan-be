# app/services/recipe_corpus.py
import os, json, time
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv
from openai import OpenAI
import json

from app.services.pinecone_client import get_pinecone_index

load_dotenv(override=True)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

RECIPES_NS = "recipes"



def _as_list(x) -> List[str]:
    if x is None:
        return []
    if isinstance(x, list):
        return [str(i).strip() for i in x if str(i).strip()]
    if isinstance(x, str):
        return [s.strip() for s in x.split(",") if s.strip()]
    return []

def _embed_texts(texts: List[str]) -> List[List[float]]:
    resp = client.embeddings.create(model="text-embedding-3-large", input=texts)
    return [d.embedding for d in resp.data]

def _recipe_to_search_text(r: Dict[str, Any]) -> str:
    ings = ", ".join([i.get("name","") for i in r.get("ingredients", []) if i.get("name")])
    tags = ", ".join(r.get("tags", []))
    return f"{r.get('title','')}. Tags: {tags}. Ingredients: {ings}. Time: {r.get('time_minutes','?')} minutes."

def _new_recipe_id(prefix: str = "r") -> str:
    # stable-enough unique id without DB
    return f"{prefix}_{int(time.time() * 1000)}"

# ---------- generation ----------

def generate_recipe_cards(payload: Dict[str, Any], n: int = 20) -> List[Dict[str, Any]]:
    diet = payload.get("diet") or payload.get("food_preference") or "any"
    cuisines = _as_list(payload.get("cuisines") or payload.get("cuisinePreference"))
    pantry = _as_list(payload.get("ingredients_at_home") or payload.get("ingredientsAtHome") or payload.get("available_ingredients"))
    exclusions = _as_list(payload.get("exclusions") or payload.get("includeIngredients"))

    user_prompt = {
        "task": "Generate recipe cards for a recipe corpus.",
        "count": n,
        "constraints": {
            "diet": diet,
            "cuisines": cuisines or ["any"],
            "pantry_bias": pantry,
            "exclude": exclusions,
            "time_minutes_max": 35,
            "steps_range": [3, 7],
            "ingredients_range": [6, 12]
        },
        "required_fields_per_recipe": {
            "id": "string",
            "title": "string",
            "tags": ["string"],
            "time_minutes": "number",
            "kcal": "number",
            "ingredients": [{"name": "string", "qty": "number|null", "unit": "string|null"}],
            "steps": ["string"]
        },
        "rules": [
            "Return ONLY valid JSON.",
            "Return an OBJECT with a single key 'recipes' whose value is an array of recipe objects.",
            "Each recipe id must be unique.",
            "Avoid excluded ingredients strictly.",
            "Prefer overlap across recipes so grocery lists reuse items.",
            "Keep ingredient names simple (no 'chopped', 'minced', etc.)."
        ],
        "output_example_shape": {
            "recipes": [
                {
                    "id": "r_001",
                    "title": "Example",
                    "tags": ["quick"],
                    "time_minutes": 20,
                    "kcal": 500,
                    "ingredients": [{"name": "eggs", "qty": 2, "unit": "count"}],
                    "steps": ["Step 1", "Step 2"]
                }
            ]
        }
    }

    resp = client.chat.completions.create(
        model="gpt-4-turbo",
        temperature=0.2,
        response_format={"type": "json_object"},  # <-- important
        messages=[
            {"role": "system", "content": "You generate clean JSON for a recipe corpus."},
            {"role": "user", "content": json.dumps(user_prompt)},
        ],
    )

    
    content = resp.choices[0].message.content
    data = json.loads(content)

    
    recipes = data.get("recipes", data)

    
    if isinstance(recipes, str):
        recipes = json.loads(recipes)

    
    if isinstance(recipes, list) and recipes and isinstance(recipes[0], str):
        fixed = []
        for s in recipes:
            try:
                fixed.append(json.loads(s))
            except Exception:
                # if it's not JSON, skip it
                continue
        recipes = fixed

    if not isinstance(recipes, list):
        raise ValueError(f"Expected list of recipes, got: {type(recipes)} -> {recipes}")

    
    cleaned: List[Dict[str, Any]] = []
    for r in recipes:
        if not isinstance(r, dict):
            continue
        if not r.get("id"):
            r["id"] = _new_recipe_id("r")
        cleaned.append(r)

    return cleaned


def upsert_recipe_cards(user_id: str,recipes: List[Dict[str, Any]]) -> Dict[str, Any]:
    index = get_pinecone_index()
    if not index:
        return {"ok": False, "error": "Pinecone not configured"}

    # Optional cleanup
    cleaned = []
    for r in recipes:
        if isinstance(r, dict) and r.get("title") and r.get("ingredients") and r.get("steps"):
            cleaned.append(r)
    recipes = cleaned

    texts = [_recipe_to_search_text(r) for r in recipes]
    embs = _embed_texts(texts)

    vectors = []
    for r, e in zip(recipes, embs):
        rid = r["id"]

        ingredient_names = [
            str(i.get("name", "")).strip()
            for i in (r.get("ingredients") or [])
            if isinstance(i, dict) and str(i.get("name", "")).strip()
        ]

        meta = {
            "user_id": str(user_id),
            "title": str(r.get("title", ""))[:500],
            "tags": [str(t) for t in (r.get("tags") or []) if isinstance(t, str)][:20],  # list of strings OK
            "time_minutes": float(r.get("time_minutes") or 0) if r.get("time_minutes") is not None else None,
            "kcal": float(r.get("kcal") or 0) if r.get("kcal") is not None else None,

           
            "ingredient_names": ingredient_names[:80],  # list of strings OK
            "steps_text": " | ".join([str(s) for s in (r.get("steps") or [])])[:5000],  # string OK

           
            "ingredients_json": json.dumps(r.get("ingredients") or [])[:15000],
            "steps_json": json.dumps(r.get("steps") or [])[:15000],
        }

        # Remove None values (safer for some Pinecone setups)
        meta = {k: v for k, v in meta.items() if v is not None}

        vectors.append((rid, e, meta))

    index.upsert(vectors=vectors, namespace=RECIPES_NS)
    return {"ok": True, "count": len(vectors)}

def retrieve_recipes_for_request(user_id: str, req: Dict[str, Any], top_k: int = 30) -> List[Dict[str, Any]]:
    index = get_pinecone_index()
    if not index:
        return []

    diet = req.get("diet") or req.get("food_preference") or "any"
    cuisines = _as_list(req.get("cuisines") or req.get("cuisinePreference"))
    pantry = _as_list(req.get("ingredients_at_home") or req.get("ingredientsAtHome") or req.get("available_ingredients"))
    exclusions = _as_list(req.get("exclusions") or req.get("includeIngredients"))
    days = int(req.get("days") or 7)

    query = (
        f"Recipes for diet={diet}, cuisines={', '.join(cuisines) or 'any'}. "
        f"Pantry: {', '.join(pantry) or 'none'}. Exclude: {', '.join(exclusions) or 'none'}. "
        f"Practical meals for {days} days."
    )

    q_emb = _embed_texts([query])[0]
    res = index.query(
        vector=q_emb,
        top_k=top_k,
        include_metadata=True,
        namespace=RECIPES_NS,
        filter={"user_id": str(user_id)}
    )

    matches = res.get("matches") or []

    out: List[Dict[str, Any]] = []
    for m in matches:
        md = m.get("metadata") or {}

        # Decode full-fidelity fields stored as JSON strings
        try:
            ingredients = json.loads(md.get("ingredients_json", "[]"))
        except Exception:
            ingredients = []

        try:
            steps = json.loads(md.get("steps_json", "[]"))
        except Exception:
            steps = []

        out.append({
            "id": m.get("id"),
            "score": m.get("score"),
            "title": md.get("title"),
            "tags": md.get("tags", []),
            "time_minutes": md.get("time_minutes"),
            "kcal": md.get("kcal"),
            "ingredients": ingredients,
            "steps": steps,
            "ingredient_names": md.get("ingredient_names", []),
        })

    return out
