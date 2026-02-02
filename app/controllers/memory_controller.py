from fastapi import Body, HTTPException
from app.services.user_memory import store_memory, retrieve_memory

class MemoryController:
    @staticmethod
    def add_memory(payload: dict = Body(...)):
        user_id = payload.get("user_id") or payload.get("chat_id")
        text = payload.get("text")
        mtype = payload.get("type", "feedback")
        if not user_id or not text:
            raise HTTPException(status_code=400, detail="Missing user_id and/or text")
        return store_memory(str(user_id), str(text), str(mtype))

    @staticmethod
    def get_memory(payload: dict = Body(...)):
        user_id = payload.get("user_id") or payload.get("chat_id")
        query = payload.get("query", "User food preferences and feedback")
        if not user_id:
            raise HTTPException(status_code=400, detail="Missing user_id")
        mem = retrieve_memory(str(user_id), str(query), top_k=int(payload.get("top_k", 5)))
        return {"memory": mem}
