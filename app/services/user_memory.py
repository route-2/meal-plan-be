# app/services/user_memory.py
import os, json, time
from typing import List, Dict, Any
from dotenv import load_dotenv
from openai import OpenAI

from app.services.pinecone_client import get_pinecone_index

load_dotenv(override=True)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

MEMORY_NS = "user_memory"

def _embed(text: str) -> List[float]:
    return client.embeddings.create(model="text-embedding-3-large", input=text).data[0].embedding

def store_memory(user_id: str, text: str, mtype: str = "feedback") -> Dict[str, Any]:
    index = get_pinecone_index()
    if not index:
        return {"ok": False, "error": "Pinecone not configured"}

    mid = f"mem_{user_id}_{int(time.time()*1000)}"
    vec = _embed(text)

    meta = {
        "user_id": str(user_id),
        "type": str(mtype),
        "text": str(text)[:5000],
        "ts": int(time.time())
    }
    index.upsert(vectors=[(mid, vec, meta)], namespace=MEMORY_NS)
    return {"ok": True, "id": mid}

def retrieve_memory(user_id: str, query: str, top_k: int = 5) -> List[str]:
    index = get_pinecone_index()
    if not index:
        return []

    qvec = _embed(query)
    res = index.query(
        vector=qvec,
        top_k=top_k,
        include_metadata=True,
        namespace=MEMORY_NS,
        filter={"user_id": str(user_id)}
    )

    out = []
    for m in (res.get("matches") or []):
        md = m.get("metadata") or {}
        if md.get("text"):
            out.append(md["text"])
    return out
