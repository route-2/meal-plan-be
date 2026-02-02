# app/services/recipe_rag.py
import os
import json
from typing import Dict, Any, List, Optional, Tuple
from openai import OpenAI
from dotenv import load_dotenv

from app.services.pinecone_client import get_pinecone_index

load_dotenv(override=True)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

RECIPES_NS = "recipes"
MEMORY_NS = "user_memory"


def _embed(texts: List[str]) -> List[List[float]]:
    resp = client.embeddings.create(model="text-embedding-3-large", input=texts)
    return [d.embedding for d in resp.data]


def recipe_to_search_text(r: Dict[str, Any]) -> str:
    ings = ", ".join([i.get("name", "") for i in r.get("ingredients", []) if i.get("name")])
    tags = ", ".join(r.get("tags", []))
    minutes = r.get("time_minutes", "unknown")
    return f"{r.get('title','')}. Tags: {tags}. Ingredients: {ings}. Time: {minutes} minutes."


def upsert_recipes(recipes: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Upserts recipes into Pinecone namespace 'recipes'.
    Each recipe must have: id, title, ingredients[], steps[].
    """
    index = get_pinecone_index()
    if not index:
        return {"ok": False, "error": "Pinecone not configured"}

    texts = [recipe_to_search_text(r) for r in recipes]
    embs = _embed(texts)

    vectors = []
    for r, e in zip(recipes, embs):
        rid = r["id"]
        meta = {
            "title": r.get("title"),
            "ingredients": r.get("ingredients", []),
            "steps": r.get("steps", []),
            "tags": r.get("tags", []),
            "time_minutes": r.get("time_minutes"),
            "kcal": r.get("kcal"),
        }
        vectors.append((rid, e, meta))

    index.upsert(vectors=vectors, namespace=RECIPES_NS)
    return {"ok": True, "count": len(vectors)}


def store_user_memory(user_id: str, text: str, mtype: str = "preference") -> Dict[str, Any]:
    index = get_pinecone_index()
    if not index:
        return {"ok": False, "error": "Pinecone not configured"}

    emb = _embed([text])[0]
    mid = f"{user_id}:{mtype}:{abs(hash(text))}"

    index.upsert(
        vectors=[(mid, emb, {"user_id": user_id, "type": mtype, "text": text})],
        namespace=MEMORY_NS,
    )
    return {"ok": True, "id": mid}


def retrieve_user_memory(user_id: str, k: int = 5) -> List[str]:
    index = get_pinecone_index()
    if not index:
        return []

    q = f"User food preferences, dislikes, constraints for user_id={user_id}"
    q_emb = _embed([q])[0]

    res = index.query(vector=q_emb, top_k=k, include_metadata=True, namespace=MEMORY_NS)
    matches = res.get("matches") or []
    out = []
    for m in matches:
        md = m.get("metadata") or {}
        if md.get("user_id") == user_id and md.get("text"):
            out.append(md["text"])
    return out


def retrieve_recipes(query: str, k: int = 25) -> List[Dict[str, Any]]:
    index = get_pinecone_index()
    if not index:
        return []

    q_emb = _embed([query])[0]
    res = index.query(vector=q_emb, top_k=k, include_metadata=True, namespace=RECIPES_NS)
    matches = res.get("matches") or []

    recipes = []
    for m in matches:
        md = m.get("metadata") or {}
        recipes.append({
            "id": m.get("id"),
            "score": m.get("score"),
            "title": md.get("title"),
            "ingredients": md.get("ingredients", []),
            "steps": md.get("steps", []),
            "tags": md.get("tags", []),
            "time_minutes": md.get("time_minutes"),
            "kcal": md.get("kcal"),
        })
    return recipes


def _normalize_list(x) -> List[str]:
    if x is None:
        return []
    if isinstance(x, list):
        return [str(i).strip() for i in x if str(i).strip()]
    if isinstance(x, str):
        return [s.strip() for s in x.split(",") if s.strip()]
    return []


def build_recipe_query(data: Dict[str, Any]) -> str:
    pantry = ", ".join(_normalize_list(data.get("ingredients_at_home"))) or "none"
    cuisines = ", ".join(_normalize_list(data.get("cuisines"))) or "any"
    diet = data.get("diet") or "any"
    exclusions = ", ".join(_normalize_list(data.get("exclusions"))) or "none"
    goal = data.get("goal") or "general"
    days = int(data.get("days") or 7)
    return (
        f"Find recipes for goal={goal}, diet={diet}, cuisines={cuisines}. "
        f"Pantry ingredients: {pantry}. Exclude: {exclusions}. "
        f"Prefer practical meals for {days} days."
    )


def select_recipes(candidates: List[Dict[str, Any]], target_meals: int, data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Simple heuristic selection:
      - prefer pantry overlap
      - prefer variety in titles/tags
    """
    pantry = set([p.lower() for p in _normalize_list(data.get("ingredients_at_home"))])
    exclude = set([e.lower() for e in _normalize_list(data.get("exclusions"))])

    def score(r: Dict[str, Any]) -> float:
        ings = [i.get("name","").lower() for i in r.get("ingredients", [])]
        if any(ex in ing for ex in exclude for ing in ings):
            return -999
        overlap = sum(1 for ing in ings for p in pantry if p and p in ing)
        base = float(r.get("score") or 0)
        time_minutes = r.get("time_minutes") or 30
        time_penalty = 0.02 * max(0, time_minutes - 25)
        return base + 1.5 * overlap - time_penalty

    # sort by score
    ranked = sorted(candidates, key=score, reverse=True)

    chosen = []
    seen_titles = set()
    seen_main_tags = set()

    for r in ranked:
        if len(chosen) >= target_meals:
            break
        title = (r.get("title") or "").strip().lower()
        tags = [t.lower() for t in (r.get("tags") or [])]
        key_tag = tags[0] if tags else ""

        # encourage variety
        if title in seen_titles:
            continue
        if key_tag and key_tag in seen_main_tags and len(chosen) < target_meals * 0.7:
            continue

        chosen.append(r)
        if title:
            seen_titles.add(title)
        if key_tag:
            seen_main_tags.add(key_tag)

    # If not enough, fill (even if tags repeat)
    if len(chosen) < target_meals:
        for r in ranked:
            if len(chosen) >= target_meals:
                break
            if r not in chosen:
                chosen.append(r)

    return chosen[:target_meals]


def compile_grounded_plan(data: Dict[str, Any], recipes: List[Dict[str, Any]], memory: List[str]) -> Dict[str, Any]:
    """
    LLM is ONLY allowed to schedule and format using provided recipes.
    Returns JSON with:
      - days -> meals -> {type, recipe_id, title, steps, ingredients}
      - grocery_list aggregated
      - kroger_payload (names + quantities)
      - audit: used_recipe_ids, retrieval_summary
    """
    days = int(data.get("days") or 7)

    # compact recipes for prompt
    compact = []
    for r in recipes:
        compact.append({
            "id": r["id"],
            "title": r.get("title"),
            "time_minutes": r.get("time_minutes"),
            "kcal": r.get("kcal"),
            "tags": r.get("tags", [])[:6],
            "ingredients": r.get("ingredients", []),
            "steps": r.get("steps", [])[:8],
        })

    system = (
        "You are a meal planning system that MUST be grounded in provided recipes. "
        "You may not invent recipes or ingredients outside of the provided recipe list."
    )

    user = {
        "task": "Create a meal plan JSON grounded in provided recipes only.",
        "preferences": {
            "goal": data.get("goal"),
            "diet": data.get("diet"),
            "cuisines": data.get("cuisines", []),
            "exclusions": data.get("exclusions", []),
            "budget": data.get("budget"),
            "ingredients_at_home": data.get("ingredients_at_home", []),
            "days": days,
        },
        "user_memory": memory,
        "provided_recipes": compact,
        "output_schema": {
            "days": [
                {
                    "day": 1,
                    "meals": [
                        {
                            "type": "breakfast|lunch|dinner",
                            "recipe_id": "string (must match provided)",
                            "title": "string",
                            "kcal": "number|null",
                            "time_minutes": "number|null",
                            "steps": ["string"],
                            "ingredients": [{"name": "string", "qty": "number|null", "unit": "string|null"}],
                        }
                    ],
                }
            ],
            "grocery_list": [{"name": "string", "qty": "number|null", "unit": "string|null"}],
            "kroger_payload": [{"name": "string", "quantity": "number|null", "unit": "string|null"}],
            "audit": {
                "used_recipe_ids": ["string"],
                "retrieval_note": "string"
            }
        },
        "rules": [
            "Use exactly 3 meals per day.",
            "Every meal must reference a provided recipe_id.",
            "Return valid JSON only. No markdown.",
            "Create grocery_list by combining ingredients across all selected recipes (dedupe by name).",
            "kroger_payload should be same as grocery_list but keep names simple (no prep words).",
        ],
    }

    resp = client.chat.completions.create(
        model="gpt-4-turbo",
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": json.dumps(user)},
        ],
        temperature=0.2,
    )

    text = resp.choices[0].message.content
    return json.loads(text)
